"""Run a tool against a corpus case, measure it, and score what it produced.

WHY THIS IS A SEPARATE PROGRAM FROM score.py. Six of the eight dimensions are properties of a
DOCUMENT and `score.py` reads them off the file. Runtime, memory and reproducibility are properties
of a RUN: you cannot read them off an output, you have to execute the thing. Keeping them apart
means `score.py` stays usable on a document somebody emailed you, and nothing has to pretend to
have measured a run it never saw.

WHAT IT MEASURES, AND HOW, because a timing number with no method behind it is worth nothing:

  * WALL TIME per repetition, with the median and the spread reported rather than an average. One
    slow run on a cold cache skews a mean and tells you nothing about the tool.
  * PEAK RSS per repetition, from `os.wait4`, which returns the rusage of THAT child rather than a
    running maximum over every child the process has ever reaped. `resource.getrusage(CHILDREN)`
    is monotonic and cannot separate one run from the next -- using it would report the largest run
    so far as the cost of every run.
  * REPRODUCIBILITY as a digest comparison over the outputs, which is all the dimension is: either
    equivalent runs produced the same bytes or they did not. Reported as a yes or no, never a
    percentage.

FIVE REPETITIONS MINIMUM, because the protocol says five or more and one run is an anecdote. Fewer
is refused rather than quietly accepted.

`ru_maxrss` IS BYTES ON macOS AND KILOBYTES ON LINUX, which is a factor of 1024 waiting to be
reported as a triumph or a disaster. Normalised here, with the platform named in the output so a
reader can check.

    python3 benchmark/run.py --case 002-mbedtls-vendor-archive-cortex-m3 \\
        --command 'my-collector --map {case}/evidence/output.map.gz --out {out}' --repeat 5

`{out}` is a fresh path per repetition and MUST appear in the command -- without it there is nothing
to score and nothing to compare. `{case}` is the case directory, so a command can reach its
evidence.
"""
import argparse
import hashlib
import json
import os
import shlex
import statistics
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))

#: The protocol's own floor. One run is an anecdote.
MIN_REPEAT = 5


def _maxrss_bytes(ru_maxrss):
    """`ru_maxrss` is bytes on macOS and kilobytes on Linux. A factor of 1024, normalised once."""
    return ru_maxrss if sys.platform == 'darwin' else ru_maxrss * 1024


def _one_run(command, case_dir, out_path):
    """One repetition: wall time, peak RSS for THAT child, and what it wrote."""
    rendered = command.format(out=out_path, case=case_dir)
    argv = shlex.split(rendered)

    started = time.perf_counter()
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # os.wait4 RATHER THAN Popen.wait: it returns the rusage of THIS child. See the module note.
    (_pid, status, usage) = os.wait4(process.pid, 0)
    elapsed = time.perf_counter() - started
    stdout, stderr = process.communicate()

    digest = None
    size = 0
    if os.path.exists(out_path):
        with open(out_path, 'rb') as handle:
            body = handle.read()
        digest = hashlib.sha256(body).hexdigest()
        size = len(body)

    return {
        'Seconds': round(elapsed, 4),
        'PeakRssBytes': _maxrss_bytes(usage.ru_maxrss),
        'ExitStatus': os.waitstatus_to_exitcode(status),
        'OutputDigest': digest,
        'OutputBytes': size,
        'Stderr': (stderr or b'').decode('utf-8', errors='replace')[:400],
    }


def measure(command, case_dir, repeat):
    if '{out}' not in command:
        sys.exit('the command must contain {out}: without it there is nothing to score.')
    if repeat < MIN_REPEAT:
        sys.exit(f'--repeat {repeat} is below the protocol\'s floor of {MIN_REPEAT}. '
                 f'One run is an anecdote.')

    runs = []
    directory = tempfile.mkdtemp(prefix='benchmark-run-')
    for index in range(repeat):
        runs.append(_one_run(command, case_dir, os.path.join(directory, f'out-{index}')))

    failed = [one for one in runs if one['ExitStatus'] != 0]
    seconds = [one['Seconds'] for one in runs]
    digests = {one['OutputDigest'] for one in runs}

    return {
        'Repetitions': repeat,
        'Failed': len(failed),
        'SecondsMedian': round(statistics.median(seconds), 4),
        'SecondsMin': min(seconds),
        'SecondsMax': max(seconds),
        # THE SPREAD, NOT A MEAN. One slow run on a cold cache skews an average and says nothing.
        'SecondsSpread': round(max(seconds) - min(seconds), 4),
        'PeakRssBytes': max(one['PeakRssBytes'] for one in runs),
        'Platform': sys.platform,
        'Reproducible': len(digests) == 1 and None not in digests,
        'Digests': sorted(one for one in digests if one),
        'Runs': runs,
        'LastOutput': os.path.join(directory, f'out-{repeat - 1}'),
        'Directory': directory,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True)
    parser.add_argument('--command', required=True,
                        help='the tool, with {out} for its output path and {case} for the case dir')
    parser.add_argument('--repeat', type=int, default=MIN_REPEAT)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    sys.path.insert(0, HERE)
    import score as scoring

    case_dir = os.path.join(scoring.CASES, args.case)
    if not os.path.isdir(case_dir):
        sys.exit(f'No such case: {args.case}. Try `score.py --list`.')

    measured = measure(args.command, case_dir, args.repeat)

    if measured['Failed']:
        first = next(one for one in measured['Runs'] if one['ExitStatus'] != 0)
        print(f"{measured['Failed']} of {measured['Repetitions']} runs failed. "
              f"First exit status {first['ExitStatus']}.", file=sys.stderr)
        if first['Stderr']:
            print(f"  stderr: {first['Stderr']}", file=sys.stderr)
        # NOT SCORED. Scoring whatever a failed run happened to leave behind would produce a
        # number for a tool that did not work.
        sys.exit(1)

    (meta, truth) = scoring.load_case(args.case)
    (candidate, reader) = scoring.read_candidate(measured['LastOutput'])
    result = scoring.score(truth, candidate, case_dir=case_dir)

    # THE TWO DIMENSIONS ONLY A RUN CAN SUPPLY, now measured rather than taken on trust.
    result['Dimensions']['RuntimeSeconds'] = measured['SecondsMedian']
    result['Dimensions']['Reproducible'] = measured['Reproducible']
    result['Measurement'] = {key: measured[key] for key in
                            ('Repetitions', 'SecondsMedian', 'SecondsMin', 'SecondsMax',
                             'SecondsSpread', 'PeakRssBytes', 'Platform', 'Reproducible',
                             'Digests')}

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(scoring.render(result, meta, reader))
    print()
    print('MEASURED OVER THE RUN')
    measurement = result['Measurement']
    print(f"  repetitions            {measurement['Repetitions']}")
    print(f"  seconds (median)       {measurement['SecondsMedian']}  "
          f"min {measurement['SecondsMin']}  max {measurement['SecondsMax']}  "
          f"spread {measurement['SecondsSpread']}")
    print(f"  peak RSS               {measurement['PeakRssBytes'] / (1024 * 1024):.1f} MB "
          f"({measurement['Platform']})")
    print(f"  reproducible           {'yes' if measurement['Reproducible'] else 'NO'}"
          f"{'' if measurement['Reproducible'] else '  -- ' + str(len(measurement['Digests'])) + ' distinct outputs'}")


if __name__ == '__main__':
    main()
