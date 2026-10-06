import fs from 'node:fs';
if(!fs.existsSync('.openai/hosting.json'))fs.copyFileSync('.openai/hosting.example.json','.openai/hosting.json');
