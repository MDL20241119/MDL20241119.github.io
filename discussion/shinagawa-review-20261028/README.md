# Encrypted discussion package

This review branch adds an encrypted, offline document package. It does not change the published site.

Download the complete package folder, including `payload/`, and open `index.html` in a current browser. A self-contained HTML copy is also supplied with the review artifacts. Obtain the passphrase separately from the document owner. The passphrase is not stored in this repository.

The package contains the discussion document, an A4 overview, speaker notes, Q&A, change notes, citations, and editable source. The PDFs also require the same passphrase. Editable source is available after unlocking.

The content uses AES-256-GCM with a fresh 16-byte salt, a fresh 12-byte IV, and PBKDF2-HMAC-SHA256 with 600,000 iterations. Decryption and downloads run locally in the browser. The document makes no background network requests. Cited sources open only when selected.

This is a shared passphrase scheme. It does not provide identity-based revocation, viewing logs, or control of copies after decryption. Handle extracted material under the applicable internal document rules.

The source archive includes its own editing and rebuild instructions. `tools/seal.py` and `tools/gate.template.html` are generic packaging code. Do not commit clear source, passwords, PDFs, or previews to this public repository.

No site deployment or external sending is included in this update.
