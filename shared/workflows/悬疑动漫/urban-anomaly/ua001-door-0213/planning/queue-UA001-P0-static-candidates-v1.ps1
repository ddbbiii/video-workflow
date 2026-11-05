[CmdletBinding()]
param(
    [string]$ComfyUrl = 'http://127.0.0.1:8188',
    [string]$RunId = (Get-Date -Format 'yyyyMMdd-HHmmss'),
    [int]$Width = 768,
    [int]$Height = 432,
    [int]$TimeoutSeconds = 1800
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$projectRoot = 'E:\program\1project\video'
$runRoot = Join-Path $projectRoot "production\series\urban-anomaly-archives\episodes\UA001-door-0213\review\runs\UA001-P0-static-candidates-v1\$RunId"
$comfyOutput = 'E:\program\1project\video\shared\runtime\comfy\models\output'
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

$commonPositive = 'mature psychological suspense anime environment, grounded adult television-anime visual language, restrained semi-realistic cel shading, controlled fine dark linework, low-key practical lighting, deep coherent shadows, desaturated cold gray-blue and blue-black palette, subtle worn texture, 16:9 landscape, no people, no readable text'
$commonNegative = 'person, character, human, silhouette, hands, cute, chibi, pastel, pink, warm luxury interior, cozy, photorealistic, live action, 3d render, text, letters, numbers, watermark, logo, signature, vertical, pillarbox, collage, split screen, fisheye, distorted perspective'

$jobs = @(
    [ordered]@{ id='UA001-SCN-001-A'; seed=[UInt64]8100101; label='SCN-001 corridor'; positive='empty old third-floor apartment corridor at night, clear one-point perspective, continuous cold-gray walls, charcoal worn floor, exactly one dark apartment door marked by an unlettered number plaque on the right side, regular round cold-white ceiling lamps, dim emergency light at vanishing point, eye-level stable establishing shot, strong spatial readability' },
    [ordered]@{ id='UA001-SCN-002-A'; seed=[UInt64]8100102; label='SCN-002 door 713'; positive='close view of one old apartment door in the same cold-gray corridor, dark blue-black painted door, peephole, lock and handle, narrow cold cyan-white light leaking from the lower door gap, torn blank paper seal beside the frame, normal opaque door, no person, no hand, stable normal-lens composition' },
    [ordered]@{ id='UA001-SCN-003-A'; seed=[UInt64]8100103; label='SCN-003 inner corridor'; positive='view through a partially opened dark apartment doorway into an impossible inner corridor, same old apartment materials but darker blue-black, one-point perspective subtly wrong, ceiling lights farther apart than expected, empty, no silhouette, doorway frame visible as foreground, controlled unsettling architecture, stable normal lens' },
    [ordered]@{ id='UA001-OBJ-003-A'; seed=[UInt64]8100104; label='OBJ seal record'; positive='top-down evidence photograph of a torn blank apartment door seal, a worn maintenance work order and a metal door key on a cold gray desk, paper areas intentionally empty for later text overlay, subdued navy ink stamp shape without letters, documentary evidence composition, no hands' },
    [ordered]@{ id='UA001-UI-001-A'; seed=[UInt64]8100105; label='UI archive card'; positive='minimal dark archival document interface background, blue-black matte card, thin cold cyan-gray rectangular border, blank title and body fields reserved for later typography, small empty square seal area, restrained surveillance archive aesthetic, flat front-facing graphic layout, no letters or numbers' },
    [ordered]@{ id='UA001-UI-002-A'; seed=[UInt64]8100106; label='UI CCTV frame'; positive='minimal dark surveillance monitor frame overlay mockup on black-blue background, thin muted cyan-gray corner lines, small blank recording indicator area, large central transparent-looking empty viewport area, clean flat graphic design, all textual areas empty for later typography, no letters or numbers' }
)

function New-Workflow([System.Collections.IDictionary]$Job) {
    $positive = "$commonPositive, $($Job.positive)"
    [ordered]@{
        '1' = @{ class_type='CheckpointLoaderSimple'; inputs=@{ ckpt_name='counterfeitxl-v2.5.safetensors' } }
        '2' = @{ class_type='CLIPTextEncode'; inputs=@{ text=$positive; clip=@('1',1) } }
        '3' = @{ class_type='CLIPTextEncode'; inputs=@{ text=$commonNegative; clip=@('1',1) } }
        '4' = @{ class_type='EmptyLatentImage'; inputs=@{ width=$Width; height=$Height; batch_size=1 } }
        '5' = @{ class_type='KSampler'; inputs=@{ model=@('1',0); positive=@('2',0); negative=@('3',0); latent_image=@('4',0); seed=$Job.seed; steps=24; cfg=5.8; sampler_name='dpmpp_2m'; scheduler='karras'; denoise=1.0 } }
        '6' = @{ class_type='VAEDecode'; inputs=@{ samples=@('5',0); vae=@('1',2) } }
        '7' = @{ class_type='SaveImage'; inputs=@{ images=@('6',0); filename_prefix="series/urban-anomaly-archives/UA001/$RunId/$($Job.id)" } }
    }
}

function Submit-Workflow([hashtable]$Prompt, [string]$ClientId) {
    $body = @{prompt=$Prompt; client_id=$ClientId} | ConvertTo-Json -Depth 20
    $response = Invoke-RestMethod -Uri "$ComfyUrl/prompt" -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 60
    if ((@($response.PSObject.Properties | ForEach-Object Name) -contains 'node_errors') -and $response.node_errors -and @($response.node_errors.PSObject.Properties).Count -gt 0) { throw ($response.node_errors | ConvertTo-Json -Depth 12) }
    return [string]$response.prompt_id
}

function Wait-ForOutput([string]$PromptId, [datetime]$Deadline) {
    while ((Get-Date) -lt $Deadline) {
        $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$PromptId" -TimeoutSec 15
        if ($history.PSObject.Properties.Name -contains $PromptId) {
            $entry = $history.PSObject.Properties[$PromptId].Value
            if ($entry.status.status_str -eq 'error') { throw ($entry.status | ConvertTo-Json -Depth 12) }
            if ($entry.status.completed) {
                $image = $entry.outputs.'7'.images[0]
                return Join-Path $comfyOutput (Join-Path $image.subfolder $image.filename)
            }
        }
        Start-Sleep -Seconds 3
    }
    throw "Timed out: $PromptId"
}

function New-ContactSheet([object[]]$Items, [string]$Path) {
    Add-Type -AssemblyName System.Drawing
    $thumbW=384; $thumbH=216; $labelH=32; $margin=14; $header=44; $columns=2
    $rows=[math]::Ceiling(@($Items).Count/$columns)
    $sheet=New-Object System.Drawing.Bitmap (($margin*($columns+1))+$thumbW*$columns),($header+$margin*($rows+1)+($thumbH+$labelH)*$rows)
    $g=[System.Drawing.Graphics]::FromImage($sheet)
    try {
        $g.Clear([System.Drawing.Color]::FromArgb(15,18,23)); $g.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $title=New-Object System.Drawing.Font('Segoe UI',14,[System.Drawing.FontStyle]::Bold); $label=New-Object System.Drawing.Font('Segoe UI',10,[System.Drawing.FontStyle]::Bold); $brush=New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
        try {
            $g.DrawString('UA001 P0 — review-only static candidates', $title,$brush,$margin,10)
            for($i=0;$i -lt @($Items).Count;$i++) { $col=$i%$columns; $row=[math]::Floor($i/$columns); $x=$margin+$col*($thumbW+$margin); $y=$header+$margin+$row*($thumbH+$labelH+$margin); $src=[System.Drawing.Image]::FromFile($Items[$i].output); try{$g.DrawImage($src,$x,$y,$thumbW,$thumbH)}finally{$src.Dispose()}; $g.DrawString($Items[$i].label,$label,$brush,$x,$y+$thumbH+4) }
            $sheet.Save($Path,[System.Drawing.Imaging.ImageFormat]::Png)
        } finally {$title.Dispose();$label.Dispose();$brush.Dispose()}
    } finally {$g.Dispose();$sheet.Dispose()}
}

$queue=Invoke-RestMethod -Uri "$ComfyUrl/queue" -TimeoutSec 15
if(@($queue.queue_running).Count -or @($queue.queue_pending).Count){throw 'Refusing to submit: ComfyUI queue is not empty.'}
$started=Get-Date; $deadline=$started.AddSeconds($TimeoutSeconds); $queued=@(); $results=@()
foreach($job in $jobs){
    $existing = @(Get-ChildItem -LiteralPath (Join-Path $comfyOutput "series\urban-anomaly-archives\UA001\$RunId") -Filter "$($job.id)_*.png" -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -First 1)
    if($existing.Count -gt 0){
        $results += [pscustomobject]@{id=$job.id;label=$job.label;seed=$job.seed;prompt_id=$null;prompt_path=$null;output=$existing[0].FullName;sha256=(Get-FileHash -LiteralPath $existing[0].FullName -Algorithm SHA256).Hash.ToLowerInvariant();status='pending-user-review';promotion='forbidden-until-explicit-approval';recovered_from_interrupted_submission=$true}
        continue
    }
    $wf=New-Workflow $job; $promptPath=Join-Path $runRoot "$($job.id)-prompt.json"; $wf|ConvertTo-Json -Depth 20|Set-Content -LiteralPath $promptPath -Encoding utf8; $promptId=Submit-Workflow $wf "ua001-p0-$RunId-$($job.id)"; $queued += [pscustomobject]@{id=$job.id;label=$job.label;seed=$job.seed;prompt_id=$promptId;prompt_path=$promptPath;positive_prompt="$commonPositive, $($job.positive)";negative_prompt=$commonNegative}
}
foreach($item in $queued){$output=Wait-ForOutput $item.prompt_id $deadline; $results += [pscustomobject]@{id=$item.id;label=$item.label;seed=$item.seed;prompt_id=$item.prompt_id;prompt_path=$item.prompt_path;output=$output;sha256=(Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash.ToLowerInvariant();status='pending-user-review';promotion='forbidden-until-explicit-approval'}}
$sheet=Join-Path $runRoot 'UA001-P0-static-candidates-v1-contact-sheet.png'; New-ContactSheet $results $sheet
$observedFiles = @($results | ForEach-Object { Get-Item -LiteralPath $_.output } | Sort-Object LastWriteTime)
$observedStart = $observedFiles[0].LastWriteTime
$observedEnd = $observedFiles[-1].LastWriteTime
$manifest=[ordered]@{run_id=$RunId;status='pending-user-review';created_at=$started.ToString('o');completed_at=(Get-Date).ToString('o');manifest_assembly_elapsed_seconds=[math]::Round(((Get-Date)-$started).TotalSeconds,2);observed_output_window_start=$observedStart.ToString('o');observed_output_window_end=$observedEnd.ToString('o');observed_output_window_seconds=[math]::Round(($observedEnd-$observedStart).TotalSeconds,2);timing_note='Observed file timestamps include two interrupted script submissions before recovery; they are not a clean single-run inference benchmark.';purpose='UA001 review-only P0 scene, evidence and blank UI candidates';resolution="$Width`x$Height";checkpoint='counterfeitxl-v2.5.safetensors';contact_sheet=$sheet;results=$results;approval_gate='No output is a formal asset or ComfyUI approved input until explicit user approval.'}
$manifestPath=Join-Path $runRoot 'UA001-P0-static-candidates-v1-manifest.json';$manifest|ConvertTo-Json -Depth 15|Set-Content -LiteralPath $manifestPath -Encoding utf8
[pscustomobject]@{run_root=$runRoot;contact_sheet=$sheet;manifest=$manifestPath;observed_output_window_seconds=$manifest.observed_output_window_seconds;count=@($results).Count}|ConvertTo-Json -Compress
