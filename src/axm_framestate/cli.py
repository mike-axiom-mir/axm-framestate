from __future__ import annotations
import argparse,json
from pathlib import Path
from .canonical import load_project,canonical_json
from .capabilities import analyze_requirements,capability_summary
from .forge import adopt_effect,spawn_effect
from .receipts import render_with_receipt,verify_repeat
from .snapshot import create_daily_snapshot
from .review import review_project
from .director import compile_plan_file
from .shots import derive_shots,storyboard
from .queue import render_queue
from .analysis import analyze_render

def _root(): return Path.cwd().resolve()
def _print(v): print(json.dumps(v,indent=2,sort_keys=True,ensure_ascii=False))

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(prog='framestate');sub=p.add_subparsers(dest='command',required=True)
    x=sub.add_parser('inspect');x.add_argument('project')
    x=sub.add_parser('render');x.add_argument('project');x.add_argument('output');x.add_argument('--no-assemble',action='store_true');x.add_argument('--profile',choices=['fast','h264','quality'],default='h264')
    x=sub.add_parser('verify-repeat');x.add_argument('project');x.add_argument('output')
    x=sub.add_parser('snapshot');x.add_argument('--output-dir')
    x=sub.add_parser('review');x.add_argument('project')
    sub.add_parser('capabilities')
    x=sub.add_parser('gaps');x.add_argument('requirements')
    x=sub.add_parser('spawn-effect');x.add_argument('candidate');x.add_argument('output')
    x=sub.add_parser('adopt-effect');x.add_argument('candidate_dir');x.add_argument('--reason',required=True);x.add_argument('--root-fit',required=True)
    x=sub.add_parser('compile-plan');x.add_argument('plan');x.add_argument('output_project')
    x=sub.add_parser('shots');x.add_argument('project')
    x=sub.add_parser('storyboard');x.add_argument('project');x.add_argument('output')
    x=sub.add_parser('render-queue');x.add_argument('queue')
    x=sub.add_parser('analyze');x.add_argument('render_dir');x.add_argument('--threshold-milli',type=int,default=300)
    x=sub.add_parser('make');x.add_argument('input');x.add_argument('output');x.add_argument('--profile',choices=['fast','h264','quality'],default='h264',help='accepts canonical project or shot-plan JSON and renders final video')
    a=p.parse_args(argv);root=_root()
    if a.command=='inspect':_print(load_project(Path(a.project)))
    elif a.command=='render':_print(render_with_receipt(load_project(Path(a.project)),Path(a.output),root,assemble=not a.no_assemble,profile=a.profile))
    elif a.command=='verify-repeat':
        r=verify_repeat(load_project(Path(a.project)),Path(a.output),root);_print(r);return 0 if r['passed'] else 2
    elif a.command=='snapshot':_print(create_daily_snapshot(root,output_dir=Path(a.output_dir) if a.output_dir else None))
    elif a.command=='review':_print(review_project(load_project(Path(a.project)),root))
    elif a.command=='capabilities':_print(capability_summary())
    elif a.command=='gaps':
        req=json.loads(Path(a.requirements).read_text())['required'];r=analyze_requirements(req);_print(r);return 0 if r['ready'] else 4
    elif a.command=='spawn-effect':_print(spawn_effect(Path(a.candidate),Path(a.output)))
    elif a.command=='adopt-effect':
        rf=json.loads(Path(a.root_fit).read_text());r=adopt_effect(root,Path(a.candidate_dir),a.reason,rf);_print(r);return 0 if r.get('adopted') else 3
    elif a.command=='compile-plan':_print(compile_plan_file(Path(a.plan),Path(a.output_project)))
    elif a.command=='shots':_print(derive_shots(load_project(Path(a.project))))
    elif a.command=='storyboard':_print(storyboard(load_project(Path(a.project)),Path(a.output),root))
    elif a.command=='render-queue':_print(render_queue(Path(a.queue),root))
    elif a.command=='analyze':_print(analyze_render(Path(a.render_dir),a.threshold_milli))
    elif a.command=='make':
        raw=json.loads(Path(a.input).read_text(encoding='utf-8'))
        if str(raw.get('schema','')).startswith('axm.framestate.shot-plan/'):
            temp=Path(a.output)/'compiled-project.json';compile_plan_file(Path(a.input),temp);project=load_project(temp)
        else: project=load_project(Path(a.input))
        _print(render_with_receipt(project,Path(a.output),root,assemble=True,profile=a.profile))
    return 0
