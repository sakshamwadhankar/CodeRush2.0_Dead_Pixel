const esbuild = require('esbuild');

esbuild.build({
  entryPoints: ['landing/agentation-entry.jsx'],
  bundle: true,
  outfile: 'landing/agentation-bundle.js',
  define: { 'process.env.NODE_ENV': '"development"' },
  loader: { '.js': 'jsx', '.jsx': 'jsx' }
}).then(() => {
  console.log('Successfully built landing/agentation-bundle.js');
}).catch((err) => {
  console.error(err);
  process.exit(1);
});
