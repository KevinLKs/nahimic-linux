"""Exercise the installed service, real controls and cold restart persistence."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from backend import Backend, RUNTIME
from desktop_audio import pulse, level


def wait(predicate, label, timeout=40):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        result=predicate()
        if result:return result
        time.sleep(.15)
    raise TimeoutError(label)


def main():
    b=Backend();before=b.status();original=b.settings()
    if not before['ready'] or before['applications']:
        raise RuntimeError('Run the installation check with the service ready and playback stopped')
    work=Path(tempfile.mkdtemp(prefix='nahimic-install-check-',dir='/tmp'))
    print(work,flush=True)
    results={};(work/'before.json').write_text(json.dumps({'status':before,'settings':original},indent=2)+'\n')
    target=json.loads((RUNTIME.parent/'installation.json').read_text())['target']
    def pair():
        data={s['name']:s for s in json.loads(pulse('--format=json','list','sinks'))}
        return data[target],data['nahimic_speakers']
    initial_physical,initial_virtual=pair()
    try:
        b.enabled(False)
        wait(lambda:not b.status().get('active',True),'bypass')
        results['profiles']=[b.profile(name)['profile'] for name in ('Music','Movie','Gaming','Communication')]
        b.profile(original['profile'])
        for key in ('kSet_BassBoostState','kSet_VoiceBoostState','kSet_TrebleBoostState','kSet_SpkVirtualSurroundState','kSet_CompressorState','kSet_EQState'):
            value=original['settings'][key]['value']
            b.set_setting(key,1-int(value));b.set_setting(key,int(value))
        for key in ('kSet_BassBoostGainDB','kSet_VoiceBoostGainDB','kSet_TrebleBoostGainDB','kSet_EQ125HzGainDB'):
            value=original['settings'][key]['value']
            b.set_setting(key,value+1);b.set_setting(key,value)
        results['original_parameter_roundtrips']=True
        physical,virtual=pair()
        pulse('set-sink-volume','nahimic_speakers',str(max(1,before['volume']-2))+'%')
        wait(lambda:level(pair()[0])==level(pair()[1]) and level(pair()[0])!=level(initial_physical),'virtual volume -> hardware')
        pulse('set-sink-mute','nahimic_speakers','1')
        wait(lambda:pair()[0]['mute'] and pair()[1]['mute'],'virtual mute -> hardware')
        pulse('set-sink-volume',physical['name'],*(str(v) for v in level(initial_physical)[0]))
        pulse('set-sink-mute',physical['name'],str(int(initial_physical['mute'])))
        wait(lambda:level(pair()[0])==level(pair()[1])==level(initial_physical),'hardware -> virtual')
        results['bidirectional_real_volume_and_mute']=True
        gain=original['settings']['kSet_BassBoostGainDB']['value']
        b.set_setting('kSet_BassBoostGainDB',gain+1)
        old_pid=b.status()['instance']
        subprocess.run(['systemctl','--user','restart','nahimic.service'],check=True,timeout=40)
        wait(lambda:b.status().get('ready') and b.status().get('instance')!=old_pid,'cold restart')
        assert b.settings()['settings']['kSet_BassBoostGainDB']['value']==gain+1
        assert not b.status()['enabled'] and not b.status()['active']
        b.set_setting('kSet_BassBoostGainDB',gain)
        results['parameter_and_bypass_survive_restart']=True
        b.enabled(True);wait(lambda:b.status().get('active'),'enable')
        old_pid=b.status()['instance']
        subprocess.run(['systemctl','--user','restart','nahimic.service'],check=True,timeout=40)
        wait(lambda:b.status().get('active') and b.status().get('instance')!=old_pid,'enabled restart')
        assert b.settings()['settings']['kSet_BassBoostGainDB']['value']==gain
        assert b.status()['autostart']
        results['enabled_survives_restart']=True
        results['autostart_enabled']=True
        results['passed']=True
    finally:
        b.profile(original['profile'])
        b.set_setting('kSet_BassBoostGainDB',original['settings']['kSet_BassBoostGainDB']['value'])
        b.enabled(before['enabled'])
        pulse('set-sink-volume',initial_physical['name'],*(str(v) for v in level(initial_physical)[0]))
        pulse('set-sink-mute',initial_physical['name'],str(int(initial_physical['mute'])))
        (work/'results.json').write_text(json.dumps(results,indent=2)+'\n')
        print(json.dumps(results),flush=True)


if __name__=='__main__':main()
