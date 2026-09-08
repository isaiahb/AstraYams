import React from 'react';
import {test,expect} from 'bun:test';
import {renderToStaticMarkup} from 'react-dom/server';
import {MarkdownText,AssignmentText} from '../src/ui/markdown';
test('engineering text renders headings, lists, tables and fenced code as readable elements',()=>{
 const html=renderToStaticMarkup(<MarkdownText text={'# Arm brief\n\n- Two joints\n- 200 mm reach\n\n| Check | Result |\n| --- | --- |\n| FK | Pass |\n\n```python\nprint(1)\n```'}/>);
 for(const element of ['<h1>','<ul>','<table>','<pre>'])expect(html).toContain(element);
});
test('raw HTML and unsafe links do not become active content',()=>{
 const html=renderToStaticMarkup(<MarkdownText text={'<script>alert(1)</script>\n\n[bad](javascript:alert%281%29)\n\n![remote](https://example.org/tracker.png)'}/>);
 expect(html).not.toContain('<script');expect(html).not.toContain('href="javascript:');expect(html).not.toContain('<img');
});
test('long assignments are available behind a disclosure',()=>{
 const html=renderToStaticMarkup(<AssignmentText text={'A detailed assignment. '.repeat(80)}/>);
 expect(html).toContain('<details>');expect(html).toContain('Read full assignment');expect(html).not.toContain('<details open');
});
