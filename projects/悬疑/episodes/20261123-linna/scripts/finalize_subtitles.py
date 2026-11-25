"""Generate shared-timeline subtitles only after recorded body review."""
from pathlib import Path
import argparse, json, os, subprocess, sys

EP=Path(__file__).resolve().parents[1]
ROOT=EP.parents[3]
os.environ['PATH']='/Users/mac/bin:'+os.environ['PATH']
sys.path.insert(0,str(ROOT/'shared/workflows/subtitles'))
from split_srt import write_srt, read_srt, normalize


def run(part):
    review=EP/'logs/body-review.json'
    assert review.exists() and json.loads(review.read_text()).get(part)=='approved', '正文尚未获得用户审看通过，不能输出最终字幕。'
    planpath=EP/f'storyboard/{part}_SHOT_PLAN.json'
    plan=json.loads(planpath.read_text())
    subprocess.run([sys.executable,str(ROOT/'shared/workflows/script-qa/lint_narration.py'),str(planpath),
                    '--json',str(EP/f'qa/{part}-final-narration.json')],check=True)
    cues=[dict(start=s['start_frame']/24,end=(s['start_frame']+s['frames'])/24,text=s['cue']) for s in plan['shots']]
    folder=EP/f'video/srt/{part}';folder.mkdir(parents=True,exist_ok=True)
    source=folder/'source-cues.srt';write_srt(cues,source)
    final=EP/f'video/final/悬疑_林娜案{part}_正文_v1.srt'
    subprocess.run([sys.executable,str(ROOT/'shared/workflows/subtitles/split_srt.py'),str(source),
        '--out',str(final),'--cues-json',str(folder/'cues.json'),'--report',str(folder/'split-report.json'),
        '--allow-word-split'],check=True)
    actual=read_srt(final)
    assert normalize(''.join(c['text'] for c in actual))==normalize(''.join(c['text'] for c in cues)), 'G1正文不一致'
    check=subprocess.run([sys.executable,str(ROOT/'shared/workflows/subtitles/check_srt.py'),str(final),'--json'],
                         capture_output=True,text=True,check=True)
    (EP/f'qa/{part}-srt.json').write_text(check.stdout)
    assert actual[0]['start']==0
    assert abs(actual[-1]['end']-plan['frames']/24)<.001
    subprocess.run([sys.executable,str(ROOT/'shared/workflows/body-only/check_delivery.py'),
        '--video',str(final.with_suffix('.mp4')),'--srt',str(final),'--json',str(EP/f'qa/{part}-delivery.json')],check=True)
    report=json.loads((folder/'split-report.json').read_text())
    (EP/f'qa/{part}-srt_qa.md').write_text(f"# {part}字幕核对\n\n- 共用分镜时间线：{len(cues)}个旁白段，拆为{len(actual)}条字幕。\n"
        f"- 每条最多{max(len(normalize(c['text'])) for c in actual)}可见字；check_srt PASS，G1正文全量一致。\n"
        f"- 首条起点0秒，末条终点{actual[-1]['end']:.3f}秒，与正文一致。\n"
        f"- 原稿锁定，不修改原文字词；{len(report['word_splits'])}个无标点长分句按词边界拆条。\n"
        "- 估算时间轴，未对真实人声校准。\n")
    print('SUBTITLES_AND_DELIVERY_PASS',part,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('part',choices=['上集','下集'])
    run(parser.parse_args().part)
