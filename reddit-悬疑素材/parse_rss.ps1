param(
  [Parameter(Mandatory=$true)][string]$Path,
  [string]$Source = '',
  [int]$Hook = 240,
  [string]$Pool = "$PSScriptRoot\pool.jsonl"
)
$ErrorActionPreference = 'Stop'
$t = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
$entries = [regex]::Matches($t, '(?s)<entry>.*?</entry>')
$rows = @()
foreach ($e in $entries) {
  $x = $e.Value
  $title = [regex]::Match($x, '(?s)<title>(.*?)</title>').Groups[1].Value
  $link  = [regex]::Match($x, '<link href="([^"]+)"').Groups[1].Value
  $author = [regex]::Match($x, '<name>(.*?)</name>').Groups[1].Value
  $pub   = [regex]::Match($x, '<published>(.*?)</published>').Groups[1].Value
  $c     = [regex]::Match($x, '(?s)<content type="html">(.*?)</content>').Groups[1].Value
  $plain = [System.Net.WebUtility]::HtmlDecode($c)
  $plain = $plain -replace '(?s)<!--.*?-->', ' '
  $plain = $plain -replace '<[^>]+>', ' '
  $plain = ($plain -replace '\s+', ' ').Trim()
  $obj = [ordered]@{
    source = $Source
    author = $author
    title  = [System.Net.WebUtility]::HtmlDecode($title)
    url    = $link
    published = $pub
    chars  = $plain.Length
    hook   = if ($plain.Length -gt $Hook) { $plain.Substring(0, $Hook) } else { $plain }
    text   = $plain
  }
  $rows += [pscustomobject]$obj
}
if ($rows.Count -eq 0) { Write-Output "!! no entries parsed from $Path"; exit 1 }
$rows | ForEach-Object { ($_ | ConvertTo-Json -Compress -Depth 3) } | Add-Content -LiteralPath $Pool -Encoding UTF8
$i = 0
foreach ($r in $rows) {
  $i++
  Write-Output ("{0,2}. {1,6:N0}c | {2} | {3}" -f $i, $r.chars, $r.author, $r.title)
  Write-Output ("    {0}" -f $r.url)
  Write-Output ("    H: {0}" -f $r.hook)
}
Write-Output "== parsed $($rows.Count) entries from $Source into pool =="
