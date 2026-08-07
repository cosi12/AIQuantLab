/** 浏览器内查看 JSON artifact，使研究者无需手工打开文件。 */

export function JsonViewer({ value }: { value: unknown }) {
  return <pre className="json">{JSON.stringify(value, null, 2)}</pre>;
}
