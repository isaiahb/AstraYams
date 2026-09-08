import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export function MarkdownText({text,className=''}:{text:string,className?:string}){
  return <div className={`markdown ${className}`}><ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml components={{
    a:({node,...props})=><a {...props} target="_blank" rel="noopener noreferrer"/>,
    table:({node,...props})=><div className="markdown-table"><table {...props}/></div>,
    img:({alt})=><span className="inline-image-note">{alt||'Image'} · available in artifacts</span>
  }}>{text||''}</ReactMarkdown></div>;
}
export function AssignmentText({text}:{text:string}){
  if(text.length<700)return <MarkdownText text={text}/>;
  const preview=text.slice(0,260).replace(/\s+\S*$/,'')+'…';
  return <div className="assignment-text"><p>{preview}</p><details><summary>Read full assignment</summary><MarkdownText text={text}/></details></div>;
}
