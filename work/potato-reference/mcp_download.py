import asyncio,json
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def main():
    params=StdioServerParameters(command=r'E:\program\1project\douyin-media-mcp\.venv\Scripts\python.exe',args=['-m','douyin_media_mcp'],cwd=r'E:\program\1project\douyin-media-mcp')
    async with stdio_client(params) as (rd,wr):
        async with ClientSession(rd,wr) as s:
            await s.initialize()
            print('MCP connected',flush=True)
            r=await s.call_tool('download_douyin_media',{'url':'https://v.douyin.com/Q_BIC8CQMV0/','output_dir':r'E:\program\1project\video\projects\小球\episodes\potato-staircase-test\refs','filename':'douyin_original','quality':'best'})
            data=r.model_dump(mode='json')
            Path(r'E:\program\1project\video\work\potato-reference\download_result.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(data,ensure_ascii=False),flush=True)
asyncio.run(main())
