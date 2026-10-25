from local_event_review import edit, quality, qtile

def test_edit_operations():
    assert edit([],[])==0
    assert edit(['a','b'],['a'])==1
    assert edit(['a'],['b','c'])==2
    assert edit(list('kitten'),list('sitting'))==3

def test_frozen_normalization():
    assert quality('Hello, WORLD!', 'hello world')==(0,2,0,10)
    assert quality('a b', 'a c')==(1,2,1,2)
    assert quality('ＡBC 12', 'abc 12')==(0,2,0,5)

def test_linear_quantile():
    assert qtile([1,2,3,4],.5)==2.5
    assert qtile([.1,.9],.99)==.892
