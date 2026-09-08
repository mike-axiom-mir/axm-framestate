from __future__ import annotations
import argparse,json
from pathlib import Path
from .canonical import load_project,canonical_json
from .capabilities import analyze_requirements,capability_summary
from .forge import adopt_effect,spawn_effect,adopt_recipe,spawn_recipe
from .receipts import render_with_receipt,verify_repeat,render_realized_with_receipt,verify_realized_repeat
from .snapshot import create_daily_snapshot
from .review import review_project
from .director import compile_plan_file,compile_brief_file
from .shots import derive_shots,storyboard
from .queue import render_queue
from .analysis import analyze_render
from .rehearsal import rehearse_project
from .rehearsal_metrics import normalize_policy
from .prompts import interpret_prompt,prompt_project,explain_prompt_token
from .director import compile_plan,compile_brief
from .canonical import normalize_project
from .speech import write_native_wav,text_to_phonemes
from .realization import probe_machine,normalize_machine_capabilities,normalize_realization_policy,plan_realization

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
    x=sub.add_parser('compile-brief');x.add_argument('brief');x.add_argument('output_project')
    x=sub.add_parser('spawn-recipe');x.add_argument('candidate');x.add_argument('output')
    x=sub.add_parser('adopt-recipe');x.add_argument('candidate_dir');x.add_argument('--reason',required=True);x.add_argument('--root-fit',required=True)
    x=sub.add_parser('shots');x.add_argument('project')
    x=sub.add_parser('storyboard');x.add_argument('project');x.add_argument('output')
    x=sub.add_parser('render-queue');x.add_argument('queue')
    x=sub.add_parser('analyze');x.add_argument('render_dir');x.add_argument('--threshold-milli',type=int,default=300)
    x=sub.add_parser('interpret-prompt');x.add_argument('input');x.add_argument('prompt')
    x=sub.add_parser('prompt-make');x.add_argument('input');x.add_argument('prompt');x.add_argument('output');x.add_argument('--profile',choices=['fast','h264','quality'],default='h264');x.add_argument('--policy');x.add_argument('--no-rehearse',action='store_true');x.add_argument('--verify-repeat',action='store_true')
    x=sub.add_parser('explain-prompt-token');x.add_argument('token')
    x=sub.add_parser('speak-native');x.add_argument('text');x.add_argument('output');x.add_argument('--voice',default='native-neutral-1');x.add_argument('--rate-wpm',type=int,default=165)
    x=sub.add_parser('inspect-speech');x.add_argument('text')
    sub.add_parser('probe-machine')
    x=sub.add_parser('plan-realization');x.add_argument('project');x.add_argument('--machine');x.add_argument('--policy')
    x=sub.add_parser('render-adaptive');x.add_argument('project');x.add_argument('output');x.add_argument('--machine');x.add_argument('--policy');x.add_argument('--no-assemble',action='store_true');x.add_argument('--verify-repeat',action='store_true')
    x=sub.add_parser('rehearse');x.add_argument('input');x.add_argument('output');x.add_argument('--policy');x.add_argument('--profile',choices=['fast','h264','quality'],default='h264');x.add_argument('--verify-repeat',action='store_true')
    x=sub.add_parser('make');x.add_argument('input');x.add_argument('output');x.add_argument('--profile',choices=['fast','h264','quality'],default='h264',help='accepts canonical project, shot-plan or creative-brief JSON and renders final video');x.add_argument('--rehearse',action='store_true');x.add_argument('--policy');x.add_argument('--verify-repeat',action='store_true')
    a=p.parse_args(argv);root=_root()
    def creation_input(path:str,out:Path|None=None):
        raw=json.loads(Path(path).read_text(encoding='utf-8'));schema=str(raw.get('schema',''))
        if schema.startswith('axm.framestate.shot-plan/'): return compile_plan(raw)
        if schema=='axm.framestate.creative-brief/v0.1': return compile_brief(raw,root)
        return normalize_project(raw)
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
    elif a.command=='compile-brief':_print(compile_brief_file(Path(a.brief),Path(a.output_project),root))
    elif a.command=='spawn-recipe':_print(spawn_recipe(Path(a.candidate),Path(a.output)))
    elif a.command=='adopt-recipe':
        rf=json.loads(Path(a.root_fit).read_text());r=adopt_recipe(root,Path(a.candidate_dir),a.reason,rf);_print(r);return 0 if r.get('adopted') else 3
    elif a.command=='shots':_print(derive_shots(load_project(Path(a.project))))
    elif a.command=='storyboard':_print(storyboard(load_project(Path(a.project)),Path(a.output),root))
    elif a.command=='render-queue':_print(render_queue(Path(a.queue),root))
    elif a.command=='analyze':_print(analyze_render(Path(a.render_dir),a.threshold_milli))
    elif a.command=='interpret-prompt':
        project=creation_input(a.input);raw_prompt=json.loads(Path(a.prompt).read_text(encoding='utf-8'));_print(interpret_prompt(project,raw_prompt))
    elif a.command=='prompt-make':
        project=creation_input(a.input);raw_prompt=json.loads(Path(a.prompt).read_text(encoding='utf-8'));policy=json.loads(Path(a.policy).read_text(encoding='utf-8')) if a.policy else None
        _print(prompt_project(project,raw_prompt,Path(a.output),root,rehearse=not a.no_rehearse,rehearsal_policy=policy,profile=a.profile,verify_final=a.verify_repeat))
    elif a.command=='explain-prompt-token':_print(explain_prompt_token(a.token))
    elif a.command=='speak-native':_print(write_native_wav(a.text,Path(a.output),a.voice,a.rate_wpm))
    elif a.command=='inspect-speech':_print({'schema':'axm.framestate.speech-plan/v0.1','text':a.text,'phonemes':text_to_phonemes(a.text)})
    elif a.command=='probe-machine':_print(probe_machine())
    elif a.command=='plan-realization':
        project=load_project(Path(a.project));machine=json.loads(Path(a.machine).read_text(encoding='utf-8')) if a.machine else probe_machine();policy=json.loads(Path(a.policy).read_text(encoding='utf-8')) if a.policy else None;_print(plan_realization(project,machine,policy))
    elif a.command=='render-adaptive':
        project=load_project(Path(a.project));machine=json.loads(Path(a.machine).read_text(encoding='utf-8')) if a.machine else probe_machine();policy=json.loads(Path(a.policy).read_text(encoding='utf-8')) if a.policy else None;rec=render_realized_with_receipt(project,Path(a.output),root,machine,policy,assemble=not a.no_assemble)
        if a.verify_repeat: rec['repeat_verification']=verify_realized_repeat(project,Path(a.output)/'repeat-proof',root,machine,policy)
        _print(rec)
    elif a.command in {'rehearse','make'}:
        raw=json.loads(Path(a.input).read_text(encoding='utf-8'));schema=str(raw.get('schema',''))
        if schema.startswith('axm.framestate.shot-plan/'):
            temp=Path(a.output)/'compiled-project.json';compile_plan_file(Path(a.input),temp);project=load_project(temp)
        elif schema=='axm.framestate.creative-brief/v0.1':
            temp=Path(a.output)/'compiled-project.json';compile_brief_file(Path(a.input),temp,root);project=load_project(temp)
        else: project=load_project(Path(a.input))
        do_rehearse=(a.command=='rehearse') or bool(getattr(a,'rehearse',False))
        if do_rehearse:
            policy=json.loads(Path(a.policy).read_text(encoding='utf-8')) if getattr(a,'policy',None) else None
            _print(rehearse_project(project,Path(a.output),root,policy=policy,assemble_final=True,profile=a.profile,verify_final=bool(getattr(a,'verify_repeat',False))))
        else:_print(render_with_receipt(project,Path(a.output),root,assemble=True,profile=a.profile))
    return 0
