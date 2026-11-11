from confirmation_common import SPLIT_NAMESPACE,SPLIT_DIRECTORY
SELECTION_STATUS="PASS_STRICT_METADATA_SELECTED_SPEAKER_DISJOINT_AUDIO_AVAILABLE"
def source(sid='s', speaker='p', frames=128000):
    return dict(source_id=sid, speaker_id=speaker, frames=frames, duration=frames/16000,
        path='/owned/'+sid+'.wav', audio_sha256='1'*64, reference='text',
        original_split=SPLIT_NAMESPACE, split_directory=SPLIT_DIRECTORY,
        archive_member=dict(path=SPLIT_DIRECTORY+'/'+sid+'.wav'),
        header=dict(sample_rate=16000, channels=1, sample_width=2, frames=frames, PCM_sha256='2'*64))


def receipt(sources=None):
    return dict(status=SELECTION_STATUS, sources=sources or [source()], metadata_first=True,
                model_calls=0, no_concat=True, no_trim=True, no_resample=True)

