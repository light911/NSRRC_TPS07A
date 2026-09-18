"""
Check the back light guard on auto center, without EPICS or the CV-LS.

centerLoop refuses to run unless the back light is white, and forces the
configured intensity when it is. That guard is easy to break by accident and
impossible to exercise on a machine with no EPICS, so instead of importing
epicsinit (which pulls in the whole CA stack) this lifts the source of
prepareBackLightForAutoCenter straight out of the file and runs it against a
stub. It therefore tests the code that actually ships, and fails loudly if the
method is renamed or removed.

Run it from anywhere:  python3 test_autocenter.py
Exits non-zero on any failure.
"""
import io, re, ast, os, queue, threading, time, logging, sys

HERE = os.path.dirname(os.path.abspath(__file__))
src = io.open(os.path.join(HERE, 'epicsinit.py'), encoding='utf-8').read()
tree = ast.parse(src)
try:
    node = next(n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef)
                and n.name == 'prepareBackLightForAutoCenter')
except StopIteration:
    sys.exit("FAIL: epicsinit.py has no prepareBackLightForAutoCenter -- the auto "
             "center back light guard was renamed or removed")
body = ast.get_source_segment(src, node)

ns = {'time': time, 'logging': logging}
exec("class Stub:\n" + "\n".join("    " + l for l in body.splitlines()), ns)
Stub = ns['Stub']


def makeStub(colour, intensity):
    s = Stub()
    s.Par = {'CVLS': {'autocenter_intensity': 20},
             'CVLS.color': colour, 'CVLS.intensity': intensity}
    s.sendQ = queue.Queue()
    s.cvlsQ = queue.Queue()
    s.logger = logging.getLogger('stub')
    s.logger.addHandler(logging.NullHandler())
    s.logger.propagate = False
    return s


def drain(q):
    out = []
    while not q.empty():
        out.append(q.get())
    return out


fails = []
def check(label, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    if not ok:
        print(f"        got  {got}\n        want {want}")
        fails.append(label)


print("\nnon-white is refused")
for colour in ('red', 'green', 'blue', 'off', 'mixed', 'unknown'):
    s = makeStub(colour, 20)
    got = s.prepareBackLightForAutoCenter('9.1')
    msgs = drain(s.sendQ)
    check(f"{colour}: refused", got, False)
    check(f"{colour}: nothing sent to CVLS", drain(s.cvlsQ), [])
    check(f"{colour}: warned the user and completed the operation", len(msgs), 2)
    if len(msgs) != 2:
        continue
    check(f"{colour}: warned the user", msgs[0][0], 'warning')
    check(f"{colour}: operation completed as failed",
          (msgs[1][0], msgs[1][1], msgs[1][3], msgs[1][4]),
          ('updatevalue', 'centerLoop', 'operation_completed', '9.1'))
    check(f"{colour}: reason names the colour", colour in msgs[1][2], True)

print("\nwhite already at the calibrated level: runs, changes nothing")
s = makeStub('white', 20)
check("allowed", s.prepareBackLightForAutoCenter('9.2'), True)
check("no CVLS command", drain(s.cvlsQ), [])
check("no dcss message", drain(s.sendQ), [])

print("\nwhite at the wrong level: forced, then runs")
s = makeStub('white', 75)
def confirm():
    time.sleep(0.2)
    s.Par['CVLS.intensity'] = 20
threading.Thread(target=confirm, daemon=True).start()
t0 = time.time()
check("allowed", s.prepareBackLightForAutoCenter('9.3'), True)
elapsed = time.time() - t0
check("asked CVLS for the calibrated level", drain(s.cvlsQ),
      [('set_intensity', 'white', 20)])
check("waited for confirmation, did not just sleep", 0.15 < elapsed < 1.0, True)
check("no failure reported", drain(s.sendQ), [])

print("\nCVLS never confirms: warns but still centres")
s = makeStub('white', 75)
t0 = time.time()
check("allowed anyway", s.prepareBackLightForAutoCenter('9.4', timeout=0.3), True)
check("gave up after the timeout", 0.3 <= time.time() - t0 < 1.0, True)
check("no failure reported", drain(s.sendQ), [])

print("\nmissing Par keys (CVLS never published) are refused, not crashed")
s = Stub()
s.Par = {'CVLS': {'autocenter_intensity': 20}}
s.sendQ, s.cvlsQ = queue.Queue(), queue.Queue()
s.logger = logging.getLogger('stub')
try:
    check("refused", s.prepareBackLightForAutoCenter('9.5'), False)
except Exception as e:
    print(f"  FAIL  raised {e!r}"); fails.append('missing keys')

print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILURES: {fails}"))
sys.exit(1 if fails else 0)
