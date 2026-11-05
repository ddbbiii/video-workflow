param(
  [string]$OutputPath = "..\\review\\BT002-storyboard-animatic-contact-sheet-v0.png"
)

Add-Type -AssemblyName System.Drawing
$scriptDir = Split-Path -Parent $PSCommandPath
$resolvedOutput = [IO.Path]::GetFullPath((Join-Path $scriptDir $OutputPath))
[IO.Directory]::CreateDirectory((Split-Path -Parent $resolvedOutput)) | Out-Null

$shots = @(
  @{id='S01'; time='00:00–00:20'; info='断网监控亮起；首个人形'; type='cctv'; n=1},
  @{id='S02'; time='00:20–00:44'; info='走廊机位；人形在电梯口'; type='cctv'; n=1},
  @{id='S03'; time='00:44–01:11'; info='雪花闪过；小人凭空出现'; type='cctv'; n=1},
  @{id='S04'; time='01:11–01:35'; info='自动回复；第二个人形形成'; type='phone'; n=2},
  @{id='S05'; time='01:35–02:00'; info='门镜无人的走廊与线影'; type='peephole'; n=1},
  @{id='S06'; time='02:00–02:27'; info='电话：它在你背后吗？'; type='room'; n=0},
  @{id='S07'; time='02:27–02:52'; info='第三个人形贴住门板'; type='cctv'; n=3},
  @{id='S08'; time='02:52–03:16'; info='平面图长出不存在的走廊'; type='plan'; n=2},
  @{id='S09'; time='03:16–03:45'; info='十一扇门；指向 1207'; type='plan'; n=11},
  @{id='S10'; time='03:45–04:11'; info='物业称：本层没有 1207'; type='record'; n=0},
  @{id='S11'; time='04:11–04:38'; info='住户状态：已迁出（明天）'; type='record'; n=0},
  @{id='S12'; time='04:38–05:02'; info='数量到六；姿势开始变化'; type='cctv'; n=6},
  @{id='S13'; time='05:02–05:33'; info='手机中的走廊被拉长；锁响'; type='phone'; n=7},
  @{id='S14'; time='05:33–06:00'; info='监控里的她身后排着八个'; type='cctv'; n=8},
  @{id='S15'; time='06:00–06:24'; info='所有记录表面都是入口'; type='surfaces'; n=8},
  @{id='S16'; time='06:24–06:50'; info='第十一人现于前置镜头'; type='phone'; n=11},
  @{id='S17'; time='06:50–07:18'; info='1207褪色；手指铅笔线化'; type='plan'; n=11},
  @{id='S18'; time='07:18–07:43'; info='门镜里许阿姨连向第十一人'; type='peephole'; n=11},
  @{id='S19'; time='07:43–08:11'; info='规则揭示：人被图形替换'; type='record'; n=11},
  @{id='S20'; time='08:11–08:37'; info='断电后，反光面开启十一门'; type='surfaces'; n=11},
  @{id='S21'; time='08:37–09:06'; info='天亮；记录中只剩一个小人'; type='plan'; n=1}
)

$W=1920; $H=1580; $cols=3; $pad=25; $gap=15; $cardW=[int](($W-2*$pad-2*$gap)/$cols); $cardH=200
$bmp = New-Object Drawing.Bitmap $W,$H
$g = [Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [Drawing.Text.TextRenderingHint]::ClearTypeGridFit
$g.Clear([Drawing.Color]::FromArgb(9,16,29))
$titleFont = New-Object Drawing.Font('Microsoft YaHei',24,[Drawing.FontStyle]::Bold)
$subFont = New-Object Drawing.Font('Microsoft YaHei',12,[Drawing.FontStyle]::Regular)
$labelFont = New-Object Drawing.Font('Consolas',11,[Drawing.FontStyle]::Bold)
$smallFont = New-Object Drawing.Font('Microsoft YaHei',10,[Drawing.FontStyle]::Regular)
$white = New-Object Drawing.SolidBrush([Drawing.Color]::FromArgb(225,235,245))
$muted = New-Object Drawing.SolidBrush([Drawing.Color]::FromArgb(137,165,190))
$cyan = New-Object Drawing.SolidBrush([Drawing.Color]::FromArgb(112,199,232))
$accentPen = New-Object Drawing.Pen([Drawing.Color]::FromArgb(80,181,226),2)
$linePen = New-Object Drawing.Pen([Drawing.Color]::FromArgb(188,221,239),2)
$thinPen = New-Object Drawing.Pen([Drawing.Color]::FromArgb(78,137,171),1)

function Draw-Figure([int]$x,[int]$y,[int]$scale,[bool]$heavy=$false) {
  $p = if($heavy){New-Object Drawing.Pen([Drawing.Color]::FromArgb(235,238,245),4)}else{New-Object Drawing.Pen([Drawing.Color]::FromArgb(188,221,239),2)}
  $g.DrawEllipse($p,$x,$y,$scale,$scale)
  $cx=$x+[int]($scale/2); $top=$y+$scale; $bottom=$top+$scale*2
  $g.DrawLine($p,$cx,$top,$cx,$bottom)
  $g.DrawLine($p,$cx,$top+$scale,$x-$scale/2,$top+$scale/2)
  $g.DrawLine($p,$cx,$top+$scale,$x+$scale+$scale/2,$top+$scale/2)
  $g.DrawLine($p,$cx,$bottom,$x-$scale/3,$bottom+$scale)
  $g.DrawLine($p,$cx,$bottom,$x+$scale+$scale/3,$bottom+$scale)
  $p.Dispose()
}
function Draw-Corridor([int]$x,[int]$y,[int]$w,[int]$h,[int]$n) {
  $g.FillRectangle((New-Object Drawing.SolidBrush([Drawing.Color]::FromArgb(16,32,52))),$x,$y,$w,$h)
  $g.DrawRectangle($accentPen,$x,$y,$w,$h)
  $cx=$x+[int]($w/2); $cy=$y+[int]($h*.42)
  $g.DrawLine($thinPen,$x,$y,$cx,$cy); $g.DrawLine($thinPen,$x+$w,$y,$cx,$cy)
  $g.DrawLine($thinPen,$x,$y+$h,$cx,$cy); $g.DrawLine($thinPen,$x+$w,$y+$h,$cx,$cy)
  0..2 | ForEach-Object { $dx=[int](($_+1)*$w/9); $g.DrawRectangle($thinPen,$x+$dx,$y+[int]($h*.2),[int]($w*.12),[int]($h*.55)); $g.DrawRectangle($thinPen,$x+$w-$dx-[int]($w*.12),$y+[int]($h*.2),[int]($w*.12),[int]($h*.55)) }
  $count=[Math]::Min($n,8); for($i=0;$i -lt $count;$i++){ Draw-Figure ($x+25+$i*28) ($y+$h-68-($i%2)*9) 9 ($n -ge 11 -and $i -eq $count-1) }
}
function Draw-Plan([int]$x,[int]$y,[int]$w,[int]$h,[int]$n) {
  $g.FillRectangle((New-Object Drawing.SolidBrush([Drawing.Color]::FromArgb(18,33,43))),$x,$y,$w,$h)
  $g.DrawRectangle($accentPen,$x,$y,$w,$h)
  $g.DrawRectangle($thinPen,$x+20,$y+20,$w-40,$h-40)
  $g.DrawLine($thinPen,$x+35,$y+[int]($h/2),$x+$w-35,$y+[int]($h/2))
  0..5 | ForEach-Object { $dx=$x+38+$_*43; $g.DrawRectangle($thinPen,$dx,$y+29,30,28); $g.DrawRectangle($thinPen,$dx,$y+$h-57,30,28) }
  $shown=[Math]::Min($n,11); for($i=0;$i -lt $shown;$i++){ Draw-Figure ($x+52+($i%6)*43) ($y+67+[int]([Math]::Floor($i/6))*30) 6 ($n -eq 11 -and $i -eq 10) }
  if($n -ge 11){ $g.DrawLine($linePen,$x+$w-65,$y+32,$x+$w-65,$y+$h-32); $g.DrawString('1207?',$smallFont,$white,$x+$w-120,$y+5) }
}
function Draw-Phone([int]$x,[int]$y,[int]$w,[int]$h,[int]$n) {
  $pw=[int]($w*.45); $px=$x+[int](($w-$pw)/2); $py=$y+3
  $g.FillRectangle((New-Object Drawing.SolidBrush([Drawing.Color]::FromArgb(8,14,23))),$px,$py,$pw,$h-6)
  $g.DrawRectangle($linePen,$px,$py,$pw,$h-6)
  $g.FillRectangle((New-Object Drawing.SolidBrush([Drawing.Color]::FromArgb(20,49,73))),$px+8,$py+14,$pw-16,$h-34)
  $g.DrawLine($thinPen,$px+16,$py+44,$px+$pw-16,$py+44)
  $g.DrawString('ANOMALOUS CAPTURE',$labelFont,$muted,$px+14,$py+18)
  $shown=[Math]::Min($n,6); for($i=0;$i -lt $shown;$i++){ Draw-Figure ($px+25+$i*24) ($py+$h-65-($i%2)*12) 8 ($n -ge 11 -and $i -eq $shown-1) }
}
function Draw-Record([int]$x,[int]$y,[int]$w,[int]$h,[string]$caption) {
  $g.FillRectangle((New-Object Drawing.SolidBrush([Drawing.Color]::FromArgb(20,35,49))),$x,$y,$w,$h)
  $g.DrawRectangle($accentPen,$x,$y,$w,$h)
  $g.DrawString('PROPERTY / ARCHIVE',$labelFont,$cyan,$x+18,$y+16)
  0..4 | ForEach-Object { $g.DrawLine($thinPen,$x+18,$y+48+$_*20,$x+$w-18,$y+48+$_*20) }
  $g.DrawString($caption,$subFont,$white,$x+22,$y+$h-38)
}
function Draw-Surfaces([int]$x,[int]$y,[int]$w,[int]$h,[int]$n) {
  0..2 | ForEach-Object { $rx=$x+$_*[int]($w/3)+4; $rw=[int]($w/3)-8; $g.FillRectangle((New-Object Drawing.SolidBrush([Drawing.Color]::FromArgb(16,36,58))),$rx,$y+8,$rw,$h-16); $g.DrawRectangle($accentPen,$rx,$y+8,$rw,$h-16); Draw-Figure ($rx+[int]($rw/2)-7) ($y+55) 13 ($n -ge 11 -and $_ -eq 2) }
}

$g.DrawString('BT002 走廊里的人形涂鸦  ·  初步分镜 / Animatic 联系表 v0',$titleFont,$white,25,18)
$g.DrawString('低清确定性策划卡：镜头号 · 时间 · 主要信息。非正式关键帧；禁止导入 ComfyUI。',$subFont,$muted,28,58)
for($i=0;$i -lt $shots.Count;$i++) {
  $row=[int]([Math]::Floor($i/$cols)); $col=$i%$cols; $x=$pad+$col*($cardW+$gap); $y=92+$row*($cardH+12)
  $g.FillRectangle((New-Object Drawing.SolidBrush([Drawing.Color]::FromArgb(14,25,42))),$x,$y,$cardW,$cardH)
  $g.DrawRectangle((New-Object Drawing.Pen([Drawing.Color]::FromArgb(54,104,139),1)),$x,$y,$cardW,$cardH)
  $g.DrawString($shots[$i].id,$labelFont,$cyan,$x+12,$y+10)
  $g.DrawString($shots[$i].time,$labelFont,$muted,$x+55,$y+10)
  $g.DrawString($shots[$i].info,$subFont,$white,$x+12,$y+31)
  $vx=$x+12; $vy=$y+58; $vw=$cardW-24; $vh=130
  switch($shots[$i].type) {
    'cctv' { Draw-Corridor $vx $vy $vw $vh $shots[$i].n; $g.DrawString('CCTV',$labelFont,$cyan,$vx+8,$vy+8) }
    'plan' { Draw-Plan $vx $vy $vw $vh $shots[$i].n; $g.DrawString('FLOOR PLAN',$labelFont,$cyan,$vx+8,$vy+8) }
    'phone' { Draw-Phone $vx $vy $vw $vh $shots[$i].n }
    'peephole' { $g.FillEllipse((New-Object Drawing.SolidBrush([Drawing.Color]::FromArgb(16,39,62))),$vx+[int]($vw*.28),$vy,$vh,$vh); $g.DrawEllipse($accentPen,$vx+[int]($vw*.28),$vy,$vh,$vh); Draw-Figure ($vx+[int]($vw*.28)+60) ($vy+44) 10 ($shots[$i].n -ge 11) }
    'record' { Draw-Record $vx $vy $vw $vh $shots[$i].info }
    'surfaces' { Draw-Surfaces $vx $vy $vw $vh $shots[$i].n }
    default { Draw-Record $vx $vy $vw $vh $shots[$i].info }
  }
}
$g.DrawString('视觉限制：人形仅存在于记录/屏幕/平面图/门镜投影中；冷硬线条，绝不儿童化。',$smallFont,$muted,25,$H-25)
$bmp.Save($resolvedOutput,[Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Output $resolvedOutput
