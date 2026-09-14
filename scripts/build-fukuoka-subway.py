#!/usr/bin/env python3
"""Convert the city's full-train Excel columns into a bounded analysis GTFS.

The dates are analysis sample dates, never an asserted official expiry date.
Requires xlrd/openpyxl. Optional --verify-pdfs uses PyMuPDF to compare the
official 2026-04-01 station departure PDFs independently from the workbooks.
No trains are joined across columns, sheets, or JR sections outside the files.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import re
import unicodedata
import zipfile

SOURCE_PAGE = 'https://subway.city.fukuoka.lg.jp/subway/about/material.php'
REVISION_PAGE = 'https://subway.city.fukuoka.lg.jp/topics/detail.php?id=2286'
SOURCES = ['kukohakozaki_timetable.xls', 'nanakuma_timetable.xlsx']
DAY_KEYS = {'平日': 'weekday', '土曜': 'saturday', '休日': 'sunday_holiday'}


def clean_name(value):
    return unicodedata.normalize('NFKC', str(value)).replace('(福岡県)', '').strip()


def time_seconds(value):
    if value is None or value == '':
        return None
    if isinstance(value, (int, float)):
        seconds = round(value * 86400)
    elif isinstance(value, (dt.time, dt.datetime)):
        seconds = value.hour * 3600 + value.minute * 60 + value.second
    else:
        raise ValueError(f'Unrecognized time {value!r}')
    # These timetables explicitly run past midnight, but Excel stores a clock.
    # Service starts at 05:15 or later. 00:xx/01:xx belongs to the prior day.
    if seconds < 3 * 3600:
        seconds += 86400
    if not 3 * 3600 <= seconds < 27 * 3600:
        raise ValueError(f'Time outside observed operating hours: {value!r}')
    # Match the public station timetables' minute precision. Some late-night
    # Excel cells retain hidden seconds that are not printed in the timetable.
    return seconds // 60 * 60


def hms(seconds):
    return f'{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}'


def read_workbooks(source_dir):
    import xlrd
    import openpyxl
    records, sheet_counts = [], []
    for filename in SOURCES:
        if filename.endswith('.xls'):
            wb = xlrd.open_workbook(source_dir / filename)
            sheets = [(s.name, [s.row_values(r) for r in range(s.nrows)]) for s in wb.sheets()]
        else:
            wb = openpyxl.load_workbook(source_dir / filename, data_only=True)
            sheets = [(s.title, [[c.value for c in row] for row in s]) for s in wb]
        for sheet_number, (title, rows) in enumerate(sheets):
            day = next(v for k, v in DAY_KEYS.items() if k in title)
            direction = 0 if ('姪浜方面' in title or '橋本方面' in title) else 1
            family = 'nanakuma' if 'nanakuma' in filename else 'airport_hakozaki'
            starts = [r for r, row in enumerate(rows) if row[0] == '始発']
            count_before = len(records)
            for block, start in enumerate(starts):
                end = starts[block + 1] if block + 1 < len(starts) else len(rows)
                for col in range(2, len(rows[start])):
                    times = []
                    for row_number in range(start + 3, end):
                        row = rows[row_number]
                        if row[1] not in ('着', '発'):
                            continue
                        seconds = time_seconds(row[col])
                        if seconds is None:
                            continue
                        station = clean_name(row[0])
                        if times and times[-1]['name'] == station:
                            # Repeated arrival/departure rows within ONE train column.
                            times[-1]['departure' if row[1] == '発' else 'arrival'] = seconds
                            times[-1]['sourceRows'].append(row_number + 1)
                        else:
                            times.append({'name': station, 'arrival': seconds,
                                          'departure': seconds, 'sourceRows': [row_number + 1]})
                    if not times:
                        continue  # Holiday sheets retain unused header cells.
                    if len(times) < 2:
                        raise ValueError(f'Incomplete train: {filename} {title} {start} {col}')
                    if len({t['name'] for t in times}) != len(times):
                        raise ValueError(f'Repeated nonconsecutive station: {title} {col}')
                    if any(a['departure'] > b['arrival'] for a, b in zip(times, times[1:])):
                        raise ValueError(f'Nonmonotonic column: {title} {start} {col}')
                    if any(t['arrival'] > t['departure'] for t in times):
                        raise ValueError(f'Negative dwell: {title} {start} {col}')
                    route = 'nanakuma' if family == 'nanakuma' else (
                        'hakozaki' if any(t['name'] == '貝塚' for t in times) else 'airport')
                    records.append({'id': f'fcs_{family}_{sheet_number}_{block}_{col}',
                        'family': family, 'route': route, 'day': day,
                        'direction': direction, 'origin': clean_name(rows[start][col]),
                        'headsign': clean_name(rows[start+1][col]), 'times': times,
                        'source': filename, 'sheet': title, 'block': block + 1,
                        'sourceColumn': col + 1,
                        'throughCode': rows[start+2][col]})
            sheet_counts.append({'source': filename, 'sheet': title,
                                 'trips': len(records) - count_before})
    return records, sheet_counts


def verify_departures(records, source_dir):
    """Independent checks on every ordinary weekday and Saturday station page.

    Sunday differences are independently checked against the highlighted
    Saturday-only late trains. PDF source URLs and fingerprints are preserved.
    """
    import pymupdf
    mapping = {1: ('airport_hakozaki', 'weekday', 1),
               2: ('airport_hakozaki', 'weekday', 0),
               3: ('airport_hakozaki', 'saturday', 1),
               4: ('airport_hakozaki', 'saturday', 0),
               5: ('nanakuma', 'weekday', 1), 6: ('nanakuma', 'weekday', 0),
               7: ('nanakuma', 'saturday', 1), 8: ('nanakuma', 'saturday', 0)}
    results = []
    for number, (family, day, direction) in mapping.items():
        pdf = next(source_dir.glob(f'{number}_*.pdf'))
        doc = pymupdf.open(pdf)
        for page_number, page in enumerate(doc):
            # The Nakasu page has two direction panels. Other pages have one.
            # Meinohama westbound is the JR section outside the workbook.
            first = clean_name(page.get_text().splitlines()[0])
            station = re.split(r'[（(]', first)[0].strip()
            if station == '中洲川端' or (number in (2, 4) and station == '姪浜'):
                continue
            numeric = [w for w in page.get_text('words') if re.fullmatch(r'\d{1,2}', w[4])]
            left = min(w[0] for w in numeric)
            hours = [w for w in numeric if w[0] < left + 18]
            if sorted(int(w[4]) % 24 for w in hours) != list(range(0, 1)) + list(range(5, 24)):
                raise ValueError(f'Cannot identify hour column: PDF {number} page {page_number+1}')
            pdf_times = []
            for word in numeric:
                if word in hours or word[0] < max(h[2] for h in hours):
                    continue
                nearest = min(hours, key=lambda h: abs((h[1]+h[3]) / 2 - (word[1]+word[3]) / 2))
                if abs((nearest[1]+nearest[3]) / 2 - (word[1]+word[3]) / 2) > 12:
                    continue
                hour = int(nearest[4]) or 24
                pdf_times.append(hour * 60 + int(word[4]))
            expected = []
            for record in records:
                if (record['family'], record['day'], record['direction']) != (family, day, direction):
                    continue
                for stop in record['times'][:-1]:
                    if stop['name'] == station:
                        expected.append(stop['departure'] // 60)
            a, b = collections.Counter(expected), collections.Counter(pdf_times)
            results.append({'pdfNumber': number, 'page': page_number+1, 'station': station,
                'day': day, 'direction': direction, 'workbookDepartures': len(expected),
                'pdfDepartures': len(pdf_times), 'matches': a == b,
                'missingFromPdf': list((a-b).elements()), 'missingFromWorkbook': list((b-a).elements())})
    return results


def csv_bytes(fields, rows):
    buf = io.StringIO(newline='')
    writer = csv.DictWriter(buf, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode('utf-8')


def verify_current_station_pdfs(records, source_dir):
    """Check PDFs linked by current station pages, including all departures.

    The airport/Hakozaki PDFs have rotated pages and an incorrect ToUnicode
    digit map. The ten digit glyphs were visually confirmed on the rendered
    official page. Only the comparison reader normalizes them; GTFS values
    always come from the original Excel cells.
    """
    import pymupdf
    digit_map = str.maketrans({chr(ord('㻜')+i):str(i) for i in range(10)})
    specs = [
        ('meinohama',0,'姪浜','airport_hakozaki',[(0,'weekday',1),(1,'saturday',1)]),
        ('hakata',0,'博多','airport_hakozaki',[(0,'weekday',1),(1,'saturday',1),
                                          (2,'weekday',0),(3,'saturday',0)]),
        ('kaizuka',0,'貝塚','airport_hakozaki',[(0,'weekday',0),(1,'saturday',0)]),
        ('hakata',2,'博多','nanakuma',[(0,'weekday',0),(1,'saturday',0)]),
        ('hashimoto',0,'橋本','nanakuma',[(0,'weekday',1),(1,'saturday',1)])]
    manifest = {s['station']:s for s in json.loads(
        (source_dir/'subway-current-station-sources.json').read_text())}
    results = []
    for station_key,index,station,family,pages in specs:
        file = source_dir/f'current-{station_key}-{index}.pdf'
        doc = pymupdf.open(file)
        for page_number,day,direction in pages:
            page = doc[page_number]
            numeric = []
            for word in page.get_text('words'):
                number = word[4].translate(digit_map)
                # Do not treat corrupted destination-name glyphs that happen
                # to be Unicode Thai/Burmese numerals as time digits.
                if re.fullmatch(r'[0-9]{1,2}',number):
                    box = pymupdf.Rect(word[:4])*page.rotation_matrix
                    numeric.append((*box,number))
            left = min(w[0] for w in numeric)
            hours = [w for w in numeric if w[0] < left+18]
            if sorted(int(w[4])%24 for w in hours) != [0]+list(range(5,24)):
                raise ValueError(f'Cannot identify current PDF hour column: {file} {page_number+1}')
            departures = []
            for word in numeric:
                if word in hours or word[0] < max(h[2] for h in hours):
                    continue
                nearest = min(hours,key=lambda h:abs((h[1]+h[3]-word[1]-word[3])/2))
                if abs((nearest[1]+nearest[3]-word[1]-word[3])/2) > 12:
                    continue
                departures.append((int(nearest[4]) or 24)*60+int(word[4]))
            expected = [s['departure']//60 for r in records
                if (r['family'],r['day'],r['direction']) == (family,day,direction)
                for s in r['times'][:-1] if s['name'] == station]
            a,b = collections.Counter(expected),collections.Counter(departures)
            results.append({'station':station,'family':family,'day':day,'direction':direction,
                'stationPage':manifest[station_key]['page'],
                'pdfUrl':manifest[station_key]['pdfs'][index].split('#')[0],
                'pdfPage':page_number+1,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
                'workbookDepartures':len(expected),'pdfDepartures':len(departures),
                'matches':a == b,'missingFromPdf':list((a-b).elements()),
                'missingFromWorkbook':list((b-a).elements())})
    (source_dir/'subway-current-station-verification.json').write_text(
        json.dumps(results,ensure_ascii=False,indent=2))
    if not all(r['matches'] for r in results):
        raise ValueError('Current station PDF differs from Excel; see current-station-verification')
    return results


def verify_sunday_exceptions(records):
    """Verify the Saturday-only boxes visually checked in the official PDFs."""
    signature = lambda r: (r['family'], r['direction'], tuple(
        (s['name'], s['arrival'], s['departure']) for s in r['times']))
    sat = {signature(r): r for r in records if r['day'] == 'saturday'}
    sun = {signature(r): r for r in records if r['day'] == 'sunday_holiday'}
    summary = lambda r: (r['family'],r['direction'],r['origin'],r['headsign'],
                         hms(r['times'][0]['departure']))
    removed = {summary(sat[key]) for key in sat.keys()-sun.keys()}
    added = {summary(sun[key]) for key in sun.keys()-sat.keys()}
    expected_removed = {
        ('airport_hakozaki',0,'福岡空港','姪浜','24:15:00'),
        ('airport_hakozaki',0,'福岡空港','姪浜','24:35:00'),
        ('airport_hakozaki',0,'貝塚','姪浜','24:19:00'),
        ('airport_hakozaki',1,'姪浜','福岡空港','24:00:00'),
        ('airport_hakozaki',1,'姪浜','貝塚','24:11:00'),
        ('airport_hakozaki',1,'姪浜','福岡空港','24:18:00'),
        ('airport_hakozaki',1,'姪浜','博多','24:25:00'),
        ('nanakuma',0,'博多','橋本','24:30:00'),
        ('nanakuma',1,'橋本','博多','24:03:00')}
    expected_added = {('airport_hakozaki',1,'姪浜','博多','24:00:00')}
    if removed != expected_removed or added != expected_added:
        raise ValueError('Sunday exception pattern differs from official Saturday-only notes')
    return {'matches':True,'saturdayOnlyTrips':8,
        'changedTrip':'姪浜24:00発は、土曜の福岡空港行きから日曜の博多止まりに変更',
        'checkedPdfPages':[{'pdfNumber':3,'page':1},{'pdfNumber':4,'page':13},
            {'pdfNumber':4,'page':19},{'pdfNumber':7,'page':1},{'pdfNumber':8,'page':1}],
        'method':'公式PDFの土曜のみ運行表示・行先注記を目視確認し、全列車の土曜/休日差分と照合'}


def build(args):
    repo = Path(__file__).resolve().parents[1]
    records, sheet_counts = read_workbooks(args.source_dir)
    comparisons = verify_departures(records, args.source_dir) if args.verify_pdfs else []
    current_comparisons = verify_current_station_pdfs(records,args.source_dir) if args.verify_pdfs else []
    sunday_check = verify_sunday_exceptions(records)
    audit_path = args.source_dir / 'subway-pdf-comparison.json'
    audit_path.write_text(json.dumps(comparisons, ensure_ascii=False, indent=2))
    mismatches = [r for r in comparisons if not r['matches']]
    if mismatches:
        print(json.dumps(mismatches, ensure_ascii=False, indent=2))
        raise ValueError(f'{len(mismatches)} independent station timetable mismatches; see {audit_path}')

    rail = json.loads((repo / 'fukuoka-mobility/data/rail.json').read_text())
    points = {}
    for feature in rail['stations']['features']:
        props = feature['properties']
        if props['N02_004'] != '福岡市':
            continue
        family = 'nanakuma' if '七隈' in props['N02_003'] else 'airport_hakozaki'
        key = (family, props['N02_005'])
        if key not in points:
            coords = feature['geometry']['coordinates']
            points[key] = {'stop_id': 'fcs_' + props['N02_005c'], 'stop_name': props['N02_005'],
                'stop_lat': round(sum(c[1] for c in coords)/len(coords), 7),
                'stop_lon': round(sum(c[0] for c in coords)/len(coords), 7),
                'stop_desc': '国土数値情報2025の駅施設中心点。改札・入口・ホーム別の位置ではありません。',
                'location_type': 0, 'wheelchair_boarding': 0}
    used = {(r['family'], s['name']) for r in records for s in r['times']}
    if used - points.keys():
        raise ValueError(f'Unmapped stations: {used-points.keys()}')
    stops = [points[k] for k in sorted(used)]
    trips, stop_times, provenance = [], [], []
    for r in records:
        headsign = r['headsign']
        if headsign != r['times'][-1]['name']:
            headsign += f'（収録は{r["times"][-1]["name"]}まで）'
        trips.append({'route_id': 'fcs_' + r['route'], 'service_id': 'fcs_' + r['day'],
            'trip_id': r['id'], 'trip_headsign': headsign, 'direction_id': r['direction']})
        for seq, s in enumerate(r['times']):
            stop_times.append({'trip_id': r['id'], 'arrival_time': hms(s['arrival']),
                'departure_time': hms(s['departure']), 'stop_id': points[(r['family'],s['name'])]['stop_id'],
                'stop_sequence': seq+1, 'pickup_type': 1 if seq == len(r['times'])-1 else 0,
                'drop_off_type': 1 if seq == 0 else 0, 'timepoint': 1})
        provenance.append({k:v for k,v in r.items() if k != 'times'})
    dates = []
    for date_text in args.dates.split(','):
        date = dt.datetime.strptime(date_text, '%Y%m%d').date()
        # This build deliberately contains only non-holiday sample dates.
        if date_text not in {'20260914','20260915','20260916','20260917','20260918','20260919','20260920'}:
            raise ValueError('Only explicitly checked September 14–20 sample dates are enabled')
        day = 'weekday' if date.weekday() < 5 else ('saturday' if date.weekday() == 5 else 'sunday_holiday')
        dates.append({'service_id': 'fcs_'+day, 'date': date_text, 'exception_type': 1})
    files = {
        'agency.txt': csv_bytes(['agency_id','agency_name','agency_url','agency_timezone','agency_lang'],
            [{'agency_id':'fcs','agency_name':'福岡市地下鉄','agency_url':'https://subway.city.fukuoka.lg.jp/',
              'agency_timezone':'Asia/Tokyo','agency_lang':'ja'}]),
        'stops.txt': csv_bytes(list(stops[0]),stops),
        'routes.txt': csv_bytes(['route_id','agency_id','route_short_name','route_long_name','route_type','route_url','route_color'],[
            {'route_id':'fcs_airport','agency_id':'fcs','route_short_name':'K','route_long_name':'空港線（地下鉄区間）','route_type':1,'route_url':SOURCE_PAGE,'route_color':'F39800'},
            {'route_id':'fcs_hakozaki','agency_id':'fcs','route_short_name':'H','route_long_name':'箱崎線（空港線への直通を含む）','route_type':1,'route_url':SOURCE_PAGE,'route_color':'0079C2'},
            {'route_id':'fcs_nanakuma','agency_id':'fcs','route_short_name':'N','route_long_name':'七隈線','route_type':1,'route_url':SOURCE_PAGE,'route_color':'00A650'}]),
        'trips.txt': csv_bytes(list(trips[0]),trips),
        'stop_times.txt': csv_bytes(list(stop_times[0]),stop_times),
        'calendar_dates.txt': csv_bytes(['service_id','date','exception_type'], dates),
        'feed_info.txt': csv_bytes(['feed_publisher_name','feed_publisher_url','feed_lang','feed_start_date','feed_end_date','feed_version'],[
            {'feed_publisher_name':'モビリティデザインラボ（福岡市公式公開Excelを加工）','feed_publisher_url':'https://mobilitydlab.com/fukuoka-mobility/',
             'feed_lang':'ja','feed_start_date':min(x['date'] for x in dates),'feed_end_date':max(x['date'] for x in dates),
             'feed_version':'analysis-snapshot-20260915-20260401-timetable'}])}
    metadata = {'schemaVersion':1, 'provider':'福岡市交通局', 'publisher':'モビリティデザインラボ',
        'sourcePage':SOURCE_PAGE, 'revisionPage':REVISION_PAGE, 'timetableRevision':'2026-04-01',
        'retrievedAt':'2026-09-14', 'verifiedAt':'2026-09-15', 'officialExpiryDate':None,
        'analysisSampleDates':[x['date'] for x in dates],
        'validityNote':'calendar_datesは通常ダイヤを比較するために選んだ分析日です。事業者公表の有効期限ではありません。期間外は運行なしではなく未判定としてください。',
        'calendarNote':'平日・土曜・日曜/休日を別シートから取得。祝日・特別ダイヤ日はこの分析日リストに含めていません。',
        'license':'福岡市オープンデータ利用規約（CC BY 2.1 JP）・国土数値情報CC BY 4.0',
        'licenseUrl':'https://creativecommons.org/licenses/by/2.1/jp/',
        'licenseEvidence':{'sourcePage':SOURCE_PAGE,'catalog':'https://data.bodik.jp/dataset/401307_subwaytimetable-book',
            'note':'交通局オープンデータ欄にCC BY 2.1 JP表示、福岡市カタログにもCreative Commons Attributionを明示'},
        'attribution':'福岡市交通局 空港線・箱崎線・七隈線時刻表全駅版、国土数値情報（鉄道データ2025年）をモビリティデザインラボが加工',
        'sources':[{'url':SOURCE_PAGE.rsplit('/',1)[0]+'/data/'+name,'file':name,
                    'sha256':hashlib.sha256((args.source_dir/name).read_bytes()).hexdigest()} for name in SOURCES],
        'stationSource':rail['meta'], 'counts':{'tripsByDayType':dict(collections.Counter(r['day'] for r in records)),
            'trips':len(trips),'stopTimes':len(stop_times),'stops':len(stops),'uniqueStationNames':len({s['stop_name'] for s in stops}),'routes':3},
        'sheetCounts':sheet_counts,'pdfComparisons':comparisons,
        'currentStationComparisons':current_comparisons,'sundayExceptionCheck':sunday_check,
        'comparisonSources':[dict(source,sha256=hashlib.sha256((args.source_dir/source['url'].split('/')[-1]).read_bytes()).hexdigest())
            for source in json.loads((args.source_dir/'subway-pdf-sources.json').read_text())] if args.verify_pdfs else [],
        'limitations':['JR筑肥線は姪浜以西の各駅時刻が未収録。JR九州の時刻表網羅率には加算しない。',
            '公表時刻の分精度で転記。中間駅の到着時刻がない場合は発車時刻と同じ値を採用し、停車時間は補間しない。',
            '駅施設中心点を利用。改札内乗換時間、入口、段差・設備、運賃、臨時運行・運休・遅延は未反映。'],
        'tripColumnProvenance':provenance}
    files['source_metadata.json'] = json.dumps(metadata,ensure_ascii=False,indent=2).encode()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            item=zipfile.ZipInfo(name,(2026,9,15,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(item,data)
    metadata['gtfsFile']=str(args.output)
    metadata['gtfsSha256']=hashlib.sha256(args.output.read_bytes()).hexdigest()
    (args.source_dir/'subway-source-metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
    print(json.dumps({'output':str(args.output),'counts':metadata['counts'],
        'independentPdfChecks':len(comparisons),'analysisSampleDates':metadata['analysisSampleDates']},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'fukuoka-mobility/data/gtfs/fukuoka-subway-official.zip')
    parser.add_argument('--dates',default='20260914,20260915,20260919,20260920')
    parser.add_argument('--verify-pdfs',action='store_true')
    build(parser.parse_args())
