// Compilación alternativa con esbuild (sin Vite), útil en entornos sin acceso al registro de npm.
// Uso: node scripts/build-esbuild.mjs   -> genera dist/ igual que `npm run build`.
// NODE_PATH puede apuntar a una carpeta node_modules con react y react-dom ya instalados.
import { build } from 'esbuild';
import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const dist = join(root, 'dist');
rmSync(dist, { recursive: true, force: true });
mkdirSync(join(dist, 'assets'), { recursive: true });

await build({
  entryPoints: [join(root, 'src/main.tsx')],
  bundle: true, minify: true, format: 'esm', target: 'es2020', jsx: 'automatic',
  outfile: join(dist, 'assets/app.js'),
  external: ['@azure/msal-browser'], // solo se carga en modo Entra
  nodePaths: process.env.NODE_PATH ? process.env.NODE_PATH.split(':') : [],
  define: {
    'process.env.NODE_ENV': '"production"',
    // Igual que Vite: las variables VITE_* del entorno quedan disponibles en import.meta.env
    'import.meta.env': JSON.stringify(Object.fromEntries(Object.entries(process.env).filter(([k]) => k.startsWith('VITE_')))),
  },
  logLevel: 'info',
});

cpSync(join(root, 'public'), dist, { recursive: true });
const html = readFileSync(join(root, 'index.html'), 'utf8')
  .replace('<script type="module" src="/src/main.tsx"></script>', '<script type="module" src="/assets/app.js"></script>')
  .replace('</head>', '  <link rel="stylesheet" href="/assets/app.css" />\n  </head>');
writeFileSync(join(dist, 'index.html'), html);
