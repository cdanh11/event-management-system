import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src');
const findings = [];
const attributes = new Set(['aria-label', 'placeholder', 'title', 'alt']);
function visitFile(file) {
  const source = ts.createSourceFile(file, fs.readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const add = (node, text) => {
    if (!text.trim() || !/[A-Za-zÀ-ỹ]/u.test(text)) return;
    findings.push({ file: path.relative(path.dirname(root), file), line: source.getLineAndCharacterOfPosition(node.getStart(source)).line + 1, text: text.trim() });
  };
  function visit(node) {
    if (ts.isJsxText(node)) add(node, node.text);
    if (ts.isJsxAttribute(node) && attributes.has(node.name.getText(source)) && node.initializer && ts.isStringLiteral(node.initializer)) add(node, node.initializer.text);
    if (ts.isJsxExpression(node) && node.expression && (!ts.isJsxAttribute(node.parent) || attributes.has(node.parent.name.getText(source)))) {
      function literals(child) {
        if (ts.isJsxElement(child) || ts.isJsxSelfClosingElement(child) || ts.isJsxFragment(child) || ts.isCallExpression(child)) return;
        if (ts.isConditionalExpression(child)) { literals(child.whenTrue); literals(child.whenFalse); return; }
        if (ts.isBinaryExpression(child) && ![ts.SyntaxKind.QuestionQuestionToken, ts.SyntaxKind.PlusToken].includes(child.operatorToken.kind)) return;
        if (ts.isStringLiteral(child) || ts.isNoSubstitutionTemplateLiteral(child)) add(child, child.text);
        else if (!ts.isFunctionLike(child)) ts.forEachChild(child, literals);
      }
      literals(node.expression);
    }
    ts.forEachChild(node, visit);
  }
  visit(source);
}
function walk(directory) {
  for (const item of fs.readdirSync(directory, { withFileTypes: true })) {
    const file = path.join(directory, item.name);
    if (item.isDirectory()) walk(file);
    else if (file.endsWith('.tsx')) visitFile(file);
  }
}
walk(root);
console.log(JSON.stringify(findings, null, 2));
