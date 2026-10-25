from gpu_feedback_probe import start_padded_power,finish_padded_power
def test_padding_brackets_but_does_not_extend_operator_window():
    now=[100.];order=[]
    class Sampler:
        def start(self):order.append(('start',now[0]))
        def stop(self):order.append(('stop',now[0]));return {'CPU_fixture':True}
    def sleep(t):now[0]+=t
    s=Sampler();capture,start=start_padded_power(s,clock=lambda:now[0],sleep=sleep)
    now[0]+=3.0;end,stop,summary=finish_padded_power(s,clock=lambda:now[0],sleep=sleep)
    assert abs(start-capture-.35)<1e-9 and abs(stop-end-.35)<1e-9
    assert abs(end-start-3.)<1e-9 and order[0][0]=='start' and order[-1][0]=='stop'
    assert summary['CPU_fixture']
