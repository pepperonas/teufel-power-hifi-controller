/* Tests der PowerHiFi-Oberflaeche.  Ausfuehren: node --test tests/
 *
 * Vertrags-Pins fuer Zusicherungen, die CSS selbst nicht ausdruecken kann —
 * allen voran die Reihenfolge von Regeln. Jede haengt an einem Fehler, der
 * hier tatsaechlich passiert ist.
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const HTML = readFileSync(join(HERE, '..', 'public', 'index.html'), 'utf8');
const CSS = [...HTML.matchAll(/<style>([\s\S]*?)<\/style>/g)].map(m => m[1]).join('\n');

/** Zeilennummer des ersten Treffers, oder -1. */
const zeile = (re) => {
  const m = re.exec(CSS);
  return m ? CSS.slice(0, m.index).split('\n').length : -1;
};

test('der Equalizer wird auf breiten Schirmen dreispaltig', () => {
  assert.match(CSS, /@media \(min-width: 900px\)[\s\S]{0,400}?\.eq-rows\s*\{[^}]*grid-template-columns:\s*repeat\(3/);
});

test('⚠️ die Media-Query steht HINTER den Basisregeln', () => {
  /* Eine Media-Query erhoeht die Spezifitaet NICHT. Weiter oben notiert verlor
     die Dreispalten-Regel gegen `.eq-row { grid-template-columns: 1fr auto auto }`
     und blieb wirkungslos — die Seite sah aus wie vorher, obwohl der Code
     "richtig" aussah. Diese Reihenfolge ist der eigentliche Fix. */
  const basis = zeile(/^\s*\.eq-row\s*\{\s*display:\s*grid/m);
  const query = zeile(/@media \(min-width: 900px\)[\s\S]{0,400}?\.eq-row\s*\{[^}]*max-content/);
  assert.notEqual(basis, -1, 'Basisregel .eq-row nicht gefunden');
  assert.notEqual(query, -1, 'Dreispalten-Regel nicht gefunden');
  assert.ok(query > basis,
    `die Media-Query (Zeile ${query}) steht vor der Basisregel (Zeile ${basis}) und verliert damit`);
});

test('⚠️ das Label bekommt KEIN 1fr in der Dreispalten-Ansicht', () => {
  /* Mit `1fr` am Label wandern die -/+ ans rechte Spaltenende — dort stehen
     sie naeher am NAECHSTEN Band als an ihrem eigenen ("Bass … − +  Mitten").
     Die Zuordnung las sich dadurch falsch herum. */
  const block = /@media \(min-width: 900px\)[\s\S]*?\.eq-row\s*\{([^}]*)\}/.exec(CSS);
  assert.ok(block, 'Dreispalten-Regel fuer .eq-row fehlt');
  assert.ok(!/1fr/.test(block[1]), 'das Label spreizt wieder auf 1fr');
  assert.match(block[1], /max-content/, 'Label und Knoepfe halten nicht mehr zusammen');
  assert.match(block[1], /justify-content:\s*start/, 'die Gruppe ist nicht linksbuendig');
});

test('Unterpolster des Containers gilt nur OHNE geteilten Fuss', () => {
  /* Mit Fuss bringt DER seine 56 px mit; zusammen mit dem eigenen Polster
     waren es 128 statt der Haus-Norm 56. Ohne Fuss (Direktzugriff per Port)
     muss das Polster aber bleiben, sonst endet der Inhalt buendig. */
  assert.match(CSS, /body\.sh-footer-page[^{]*\.container[^{]*\{[^}]*padding-bottom:\s*0/);
});

test('der Toast-Container hebelt die Regel nicht aus', () => {
  /* `:last-of-type` griff nicht, weil nach den Karten noch `.message` steht —
     die letzte Karte war damit gar nicht die letzte. */
  assert.match(CSS, /:has\(\+\s*\.message\)/,
    'der nachfolgende .message-Container ist nicht beruecksichtigt');
});

test('geteilte Leiste und Icons stehen auf der Hausversion', () => {
  assert.match(HTML, /nav\.js\?v=21/);
  assert.match(HTML, /icons\.js\?v=9/);
});

test('Icons kommen aus dem geteilten Set, nicht als Emoji', () => {
  // Die App wurde 2026-08-14 bewusst emoji-frei gemacht.
  // Nur das GERENDERTE Markup pruefen: Stil-/Skriptbloecke und Kommentare
  // enthalten ⚠-Marker als Doku-Konvention, die nie auf dem Schirm landen.
  const markup = HTML
    .replace(/<style>[\s\S]*?<\/style>/g, '')
    .replace(/<script[\s\S]*?<\/script>/g, '')
    .replace(/<!--[\s\S]*?-->/g, '');
  const emoji = markup.match(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu) || [];
  assert.deepEqual(emoji, [], `Emoji im Markup: ${emoji.join(' ')}`);
});

test('jede Schaltflaeche mit Icon hat auch eine Beschriftung oder ein aria-label', () => {
  // Ein reines Icon ohne Namen ist fuer Screenreader stumm.
  const btns = [...HTML.matchAll(/<button\b([^>]*)>([\s\S]*?)<\/button>/g)];
  const stumm = btns.filter(([, attrs, inner]) =>
    /data-sh-icon/.test(inner) &&
    !/aria-label=/.test(attrs) &&
    !inner.replace(/<[^>]*>/g, '').trim()
  );
  assert.deepEqual(stumm.map(m => m[0].slice(0, 60)), []);
});

test('CSS-Klammern sind ausgeglichen', () => {
  const auf = (CSS.match(/\{/g) || []).length, zu = (CSS.match(/\}/g) || []).length;
  assert.equal(auf, zu);
});

test('kein style-Attribut verschluckt Markup', () => {
  // Ein fehlendes schliessendes Anfuehrungszeichen frisst das nachfolgende
  // Element — in der Hue-App genau so passiert.
  for (const m of HTML.matchAll(/style="([^"]*)"/g)) {
    assert.ok(!m[1].includes('<'), `style-Attribut verschluckt Markup: ${m[0].slice(0, 70)}`);
  }
});
