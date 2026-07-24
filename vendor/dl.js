const https = require('https'), fs = require('fs');
function dl(u, out) {
  https.get(u, res => {
    if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
      let loc = res.headers.location;
      if (loc.startsWith('/')) loc = 'https://' + u.split('/')[2] + loc;
      return dl(loc, out);
    }
    if (res.statusCode !== 200) { console.error('status', res.statusCode, u); process.exit(1); }
    const f = fs.createWriteStream(out);
    res.pipe(f);
    f.on('finish', () => { console.log('saved', out); });
  }).on('error', e => { console.error('ERR', e.message); process.exit(1); });
}
dl(process.argv[2], process.argv[3]);
