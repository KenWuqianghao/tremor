"""Tremor regression tests -- replayed from cached component scores, zero recomputation.

Every assertion is replayed from the per-file component scores and results recorded while the
chooser was being developed on the TSB-AD Tuning sets.  No series is read, no detector is run,
no VUS-PR is recomputed and TSB-AD does not need to be installed: the tests load the float32
component scores from `tests/fixtures/`, push them through the decision layer
(`tremor.fuse_components`, the same call `Tremor.fit` makes) and compare against the decisions,
the SHA-256 of the fused score arrays and the per-file VUS-PR values recorded at the time.

    python -m unittest discover -s tests -v

Fixtures (lzma-compressed .npz of float32 arrays, one entry per Tuning file):
  U: u_mmpad, u_subpca, u_point                (47 of the 48 U Tuning files; 174_MITDB is out)
  M: m_mmpad, m_point_m, m_point_m_gate        (15 of the 20 M Tuning files)
Expectations (u_results.json / m_results.json): the hyper-parameters the recorded run used,
the per-file VUS-PR of every component and of Tremor as the benchmark's own `get_metrics`
produced them, the recorded decision (weights / flat / override) and the SHA-256 of the fused
float32 score array.
"""
import hashlib
import io
import json
import lzma
import os
import unittest

import numpy as np

from tremor import DEFAULT_HP, fuse_components

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, 'tests', 'fixtures')

U_COMPONENTS = ['u_mmpad', 'u_subpca', 'u_point']            # MMPAD, Sub-PCA, point
M_COMPONENTS = ['m_mmpad', 'm_point_m', 'm_point_m_gate']    # MMPAD-M, point-M, gate series

# The numbers documented in README.md, on the Tuning sets these fixtures cover.
U_TUNING_MEAN, U_TUNING_FILES = 0.6713, 47
M_TUNING_MEAN, M_TUNING_FILES = 0.6373, 15
U_COMPONENT_MEANS = [0.4240, 0.3320, 0.4463]   # MMPAD, Sub-PCA, point
M_COMPONENT_MEANS = [0.4368, 0.4245]           # MMPAD-M, point-M (top3z)

# Files chosen to exercise every branch of the chooser (from the recorded decisions).
U_SAMPLE = ['182_SMD_id_5_Facility_tr_7174_1st_21230',        # point overrides a peaked winner
            '033_WSD_id_5_WebService_tr_4559_1st_12588',      # both flat -> highest z-max (point)
            '300_TODS_id_14_Synthetic_tr_1250_1st_2555']      # Sub-PCA beats MMPAD on kurtosis + z
U_SAMPLE_EXTRA = ['012_NAB_id_12_Synthetic_tr_1007_1st_2787',  # anchor kept (MMPAD confidently peaked)
                  '152_Stock_id_4_Finance_tr_500_1st_2',      # flat, anchor has the highest z-max
                  '583_YAHOO_id_33_WebService_tr_500_1st_1616']  # second override file
M_SAMPLE = ['011_MSL_id_10_Sensor_tr_1525_1st_4590',          # point-M overrides through the gates
            '072_SMD_id_16_Facility_tr_7119_1st_15849']       # MMPAD-M flat -> point-M


_ARRAYS = {}


def arrays(name):
    """All score arrays of one fixture, {file stem: float32 array}; decompressed once."""
    if name not in _ARRAYS:
        with open(os.path.join(FIXTURES, name + '.npz.xz'), 'rb') as f:
            npz = np.load(io.BytesIO(lzma.decompress(f.read())))
        _ARRAYS[name] = {k: npz[k] for k in npz.files}
    return _ARRAYS[name]


def results(track):
    with open(os.path.join(FIXTURES, track + '_results.json')) as f:
        return json.load(f)


U, M = results('u'), results('m')


def load_components(names, stem):
    return [arrays(n)[stem].astype(float) for n in names]


def chosen_of(info_or_result):
    return int(np.argmax(list(info_or_result['weights'])))


def overrode(info_or_result):
    """True iff the point component replaced a peaked winner.  The recorded U rows carry the
    gate statistics (`agree`, `spikes`) but no `override` flag, so it is derived the same way
    for both sides: the point component chosen outside the flat fallback."""
    if 'override' in info_or_result:
        return bool(info_or_result['override'])
    return chosen_of(info_or_result) == 2 and not bool(info_or_result['flat'])


def sha256_of(out):
    return hashlib.sha256(out.astype(np.float32).tobytes()).hexdigest()


class FixtureTest(unittest.TestCase):
    """Guard: the fixtures are present and complete."""

    def test_fixtures_are_complete(self):
        self.assertEqual(len(U['files']), U_TUNING_FILES)
        self.assertEqual(len(M['files']), M_TUNING_FILES)
        for n in U_COMPONENTS:
            self.assertEqual(sorted(arrays(n)), U['files'], n)
        for n in M_COMPONENTS:
            self.assertEqual(sorted(arrays(n)), M['files'], n)
        for stem in U['files']:
            self.assertEqual(len(arrays('u_mmpad')[stem]), U['tremor'][stem]['n'])
        for stem in M['files']:
            self.assertEqual(len(arrays('m_mmpad')[stem]), M['tremor'][stem]['n'])

    def test_arrays_are_float32(self):
        for n in U_COMPONENTS + M_COMPONENTS:
            for stem, a in arrays(n).items():
                self.assertEqual(a.dtype, np.float32, (n, stem))


class FusionDecisionTest(unittest.TestCase):
    """(a) The chooser reproduces the recorded decision on every cached Tuning file."""

    def test_u_decisions_on_sample_files(self):
        for stem in U_SAMPLE + U_SAMPLE_EXTRA:
            with self.subTest(file=stem):
                _, info = fuse_components(load_components(U_COMPONENTS, stem), DEFAULT_HP)
                self.assertEqual(chosen_of(info), chosen_of(U['tremor'][stem]))

    def test_u_decisions_on_all_47_tuning_files(self):
        for stem in U['files']:
            with self.subTest(file=stem):
                _, info = fuse_components(load_components(U_COMPONENTS, stem), DEFAULT_HP)
                rec = U['tremor'][stem]
                self.assertEqual(chosen_of(info), chosen_of(rec))
                self.assertEqual(bool(info['flat']), bool(rec['flat']))
                self.assertEqual(overrode(info), overrode(rec))

    def test_u_branch_coverage_of_the_sample(self):
        """The sample really does hit override / flat-fallback / kurtosis-override / anchor."""
        branches = set()
        for stem in U_SAMPLE + U_SAMPLE_EXTRA:
            _, info = fuse_components(load_components(U_COMPONENTS, stem), DEFAULT_HP)
            branches.add((chosen_of(info), bool(info['flat']), bool(info.get('override'))))
        self.assertIn((2, False, True), branches)    # point overrides a peaked winner
        self.assertIn((2, True, False), branches)    # flat fallback picks the point component
        self.assertIn((1, False, False), branches)   # Sub-PCA wins the kurtosis contest
        self.assertIn((0, False, False), branches)   # anchor kept
        self.assertIn((0, True, False), branches)    # flat fallback keeps the anchor

    def test_m_decisions_on_all_15_tuning_files(self):
        for stem in M['files']:
            with self.subTest(file=stem):
                _, info = fuse_components(load_components(M_COMPONENTS, stem), DEFAULT_HP, multivariate=True)
                rec = M['tremor'][stem]
                self.assertEqual(chosen_of(info), chosen_of(rec))
                self.assertEqual(bool(info['flat']), bool(rec['flat']))
                self.assertEqual(overrode(info), overrode(rec))

    def test_m_override_fires_on_exactly_two_files(self):
        fired = [s for s in M['files']
                 if fuse_components(load_components(M_COMPONENTS, s), DEFAULT_HP, multivariate=True)[1].get('override')]
        self.assertEqual([s.split('_id_')[0] for s in fired], ['011_MSL', '164_SMAP'])

    def test_gate_series_is_never_chosen_on_m(self):
        for stem in M['files']:
            _, info = fuse_components(load_components(M_COMPONENTS, stem), DEFAULT_HP, multivariate=True)
            self.assertNotEqual(chosen_of(info), 2, stem)


class UPathByteIdenticalTest(unittest.TestCase):
    """(b) The U path emits the recorded float32 score array, byte for byte (SHA-256)."""

    def test_three_files_byte_identical(self):
        for stem in U_SAMPLE:
            with self.subTest(file=stem):
                out, _ = fuse_components(load_components(U_COMPONENTS, stem), DEFAULT_HP)
                self.assertEqual(sha256_of(out), U['tremor'][stem]['sha256'])

    def test_all_47_files_byte_identical(self):
        for stem in U['files']:
            with self.subTest(file=stem):
                out, _ = fuse_components(load_components(U_COMPONENTS, stem), DEFAULT_HP)
                self.assertEqual(sha256_of(out), U['tremor'][stem]['sha256'])


class MPathByteIdenticalTest(unittest.TestCase):
    """(c) The M path emits the recorded float32 score array, byte for byte (SHA-256)."""

    def test_two_files_byte_identical(self):
        for stem in M_SAMPLE:
            with self.subTest(file=stem):
                out, _ = fuse_components(load_components(M_COMPONENTS, stem), DEFAULT_HP, multivariate=True)
                self.assertEqual(sha256_of(out), M['tremor'][stem]['sha256'])

    def test_all_15_files_byte_identical(self):
        for stem in M['files']:
            with self.subTest(file=stem):
                out, _ = fuse_components(load_components(M_COMPONENTS, stem), DEFAULT_HP, multivariate=True)
                self.assertEqual(sha256_of(out), M['tremor'][stem]['sha256'])


class DocumentedTuningMeansTest(unittest.TestCase):
    """(d) The Tuning means quoted in README.md, from the recorded per-file results.

    The VUS-PR values are the ones the benchmark's own `get_metrics` produced when each file was
    scored (`harness/common.evaluate`); they are not recomputed here.  What the tests above
    establish is that the code still selects the same component and emits the same score array
    on every one of those files -- so the recorded VUS-PR values are still this code's.
    """

    def test_u_tuning_mean_0_6713_on_47_files(self):
        mean = float(np.mean([U['tremor'][s]['VUS-PR'] for s in U['files']]))
        self.assertAlmostEqual(mean, U_TUNING_MEAN, places=4)

    def test_m_tuning_mean_0_6373_on_15_files(self):
        mean = float(np.mean([M['tremor'][s]['VUS-PR'] for s in M['files']]))
        self.assertAlmostEqual(mean, M_TUNING_MEAN, places=4)

    def test_component_means_on_the_same_files(self):
        for key, expect in zip(['mmpad', 'subpca', 'point'], U_COMPONENT_MEANS):
            mean = float(np.mean([U['components'][key][s]['VUS-PR'] for s in U['files']]))
            self.assertAlmostEqual(mean, expect, places=4, msg=key)
        for key, expect in zip(['mmpad', 'point_m'], M_COMPONENT_MEANS):
            mean = float(np.mean([M['components'][key][s]['VUS-PR'] for s in M['files']]))
            self.assertAlmostEqual(mean, expect, places=4, msg=key)

    def test_tremor_beats_every_component_it_chooses_between(self):
        self.assertGreater(float(np.mean([U['tremor'][s]['VUS-PR'] for s in U['files']])), max(U_COMPONENT_MEANS))
        self.assertGreater(float(np.mean([M['tremor'][s]['VUS-PR'] for s in M['files']])), max(M_COMPONENT_MEANS))


class HyperParameterTest(unittest.TestCase):
    """The package, the TSB-AD adapter and the recorded runs all carry the same hyper-parameters."""

    def test_adapter_hp_matches_default_hp(self):
        path = os.path.join(ROOT, 'benchmark_exp', 'Run_Tremor.py')
        ns = {}
        with open(path) as f:
            src = f.read()
        start = src.index('Tremor_HP = {')
        end = src.index('\n\nif __name__', start)
        exec(compile(src[start:end], path, 'exec'), ns)          # the literal dict only
        self.assertEqual(ns['Tremor_HP'], dict(DEFAULT_HP))

    def test_recorded_u_run_used_the_default_values(self):
        hp = U['hp']
        self.assertEqual(sorted(hp['gates']), sorted(DEFAULT_HP['override']))
        for k in ('pzmin', 'kfrac', 'athr', 'sthr', 'cthr'):
            self.assertEqual(hp[k], DEFAULT_HP[k], k)

    def test_recorded_m_run_used_the_default_values(self):
        hp = M['hp']
        self.assertEqual(sorted(hp['override']), sorted(DEFAULT_HP['override_m']))
        self.assertEqual(hp['gate'], DEFAULT_HP['gate_m'])
        self.assertEqual(hp['cthr'], DEFAULT_HP['cthr_m'])
        for k in ('pzmin', 'athr', 'sthr'):
            self.assertEqual(hp[k], DEFAULT_HP[k], k)


class SyntheticSeriesTest(unittest.TestCase):
    """The pure-numpy pieces on synthetic input (no TSB-AD needed)."""

    def test_point_score_marks_an_isolated_spike(self):
        from tremor.point import point_score
        rng = np.random.default_rng(0)
        x = rng.normal(size=2000)
        x[1000] += 40.0
        z = point_score(x, window=1)
        self.assertIn(int(np.argmax(z)), (1000, 1001))
        self.assertGreater(z.max(), 20.0)

    def test_spike_runs_and_agreement(self):
        from tremor.fusion import spike_runs, topk_agreement
        s = np.zeros(1000)
        s[100:109] = 20.0          # one run of 9 points ...
        s[500] = 20.0              # ... and one isolated point: 10 above the threshold
        self.assertEqual(spike_runs(s, sthr=10.0), 2)
        self.assertEqual(spike_runs(np.zeros(10), sthr=10.0), 0)
        other = np.zeros(1000)
        other[800:810] = 20.0      # 10 points, nowhere near s's
        self.assertEqual(topk_agreement(s, s, kfrac=0.01), 1.0)      # top-1% = 10 positions
        self.assertEqual(topk_agreement(s, other, kfrac=0.01), 0.0)

    def test_fuse_returns_ranks_of_the_chosen_component(self):
        from tremor.fusion import fuse, rank_norm
        rng = np.random.default_rng(1)
        peaked = rng.normal(size=3000); peaked[1500] = 60.0      # confidently peaked anchor
        flat = rng.normal(size=3000)
        out, info = fuse([peaked, flat], override=None)
        self.assertEqual(chosen_of(info), 0)
        np.testing.assert_array_equal(out, rank_norm(peaked))


if __name__ == '__main__':
    unittest.main(verbosity=2)
