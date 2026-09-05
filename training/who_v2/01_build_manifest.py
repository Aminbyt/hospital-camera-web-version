import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.m4v'}
DATASET_RE = re.compile(r'dataset\s*0*(\d+)', re.I)


def natural_dataset_key(p: Path):
    m = DATASET_RE.search(p.name)
    return int(m.group(1)) if m else 9999


def find_dataset_dirs(root: Path):
    ds = [p for p in root.iterdir() if p.is_dir() and DATASET_RE.search(p.name)]
    return sorted(ds, key=natural_dataset_key)


def find_child_ci(parent: Path, name: str):
    for p in parent.iterdir():
        if p.name.lower() == name.lower():
            return p
    return None


def load_annotation(path: Path):
    with path.open('r', encoding='utf-8') as f:
        obj = json.load(f)
    labels = obj.get('labels')
    if not isinstance(labels, list):
        raise ValueError(f'{path}: missing labels[]')
    extras = {k: v for k, v in obj.items() if k != 'labels'}
    return labels, extras


def consensus(vals):
    if not vals:
        return None, 0, 0.0
    c = Counter(vals)
    value, votes = c.most_common(1)[0]
    return value, votes, votes / len(vals)


def transition_mask(codes, margin):
    n = len(codes)
    mask = [False] * n
    for i in range(1, n):
        if codes[i] != codes[i - 1]:
            lo = max(0, i - margin)
            hi = min(n, i + margin + 1)
            for j in range(lo, hi):
                mask[j] = True
    return mask


def deterministic_split(key, seed=42):
    """Stable video-level 80/10/10 split. Never split frames/windows independently."""
    import hashlib
    v = int(hashlib.sha1(f'{seed}:{key}'.encode()).hexdigest()[:8], 16) % 100
    if v < 80:
        return 'train'
    if v < 90:
        return 'val'
    return 'test'


def safe_int(v):
    if pd.isna(v):
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def safe_float(v):
    if pd.isna(v):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_statistics(root: Path, explicit_path=None):
    """Load dataset-wide statistics.csv and index it by (dataset/location, video stem).

    The PSKUS file stores filename values ending in .csv. We match them by stem to the
    annotation/video stem. The malformed washing_duration field is intentionally not used.
    """
    path = Path(explicit_path).expanduser().resolve() if explicit_path else root / 'statistics.csv'
    if not path.exists():
        return None, {}, [f'statistics.csv not found at {path}; continuing without metadata']

    try:
        df = pd.read_csv(path)
    except Exception as e:
        return None, {}, [f'Could not read statistics.csv: {e}']

    required = {'filename', 'location', 'num_annotators', 'total_duration'}
    missing = required - set(df.columns)
    if missing:
        return df, {}, [f'statistics.csv missing required columns: {sorted(missing)}']

    index = {}
    warnings = []
    duplicates = []
    for _, r in df.iterrows():
        stem = Path(str(r['filename'])).stem
        location = str(r['location']).strip()
        key = (location.lower(), stem.lower())
        if key in index:
            duplicates.append(f'{location}/{stem}')
        index[key] = {
            'statistics_filename': str(r['filename']),
            'statistics_location': location,
            'num_annotators_expected': safe_int(r['num_annotators']),
            'total_duration_sec': safe_float(r['total_duration']),
            'ring': safe_int(r['ring']) if 'ring' in df.columns else None,
            'armband': safe_int(r['armband']) if 'armband' in df.columns else None,
            'long_nails': safe_int(r['long_nails']) if 'long_nails' in df.columns else None,
        }
    if duplicates:
        warnings.append(f'statistics.csv has {len(duplicates)} duplicate dataset/stem rows')
    return df, index, warnings


def load_summary(root: Path, explicit_path=None):
    path = Path(explicit_path).expanduser().resolve() if explicit_path else root / 'summary.csv'
    if not path.exists():
        return None
    try:
        raw = pd.read_csv(path, header=None)
        return {str(k).strip(): v for k, v in raw.iloc[:, :2].itertuples(index=False, name=None)}
    except Exception:
        return None


def metadata_for_video(stats_index, dataset_name, stem):
    return stats_index.get((dataset_name.lower(), stem.lower()))


def main():
    ap = argparse.ArgumentParser(description='Build AKAM WHO v2 frame/video manifests from raw PSKUS.')
    ap.add_argument('--data-root', required=True,
                    help='Folder directly containing DataSet1..DataSet11 and statistics.csv/summary.csv')
    ap.add_argument('--out', default='manifests/master_manifest.csv')
    ap.add_argument('--statistics', default=None, help='Optional explicit statistics.csv path')
    ap.add_argument('--summary', default=None, help='Optional explicit summary.csv path')
    ap.add_argument('--transition-margin', type=int, default=15,
                    help='Frames excluded on each side of WHO code changes (15 ~= 0.5 s at 30 FPS)')
    ap.add_argument('--allow-missing-video', action='store_true')
    args = ap.parse_args()

    root = Path(args.data_root).expanduser().resolve()
    if not root.exists():
        raise SystemExit(f'Data root does not exist: {root}')

    out = Path(args.out)
    if not out.is_absolute():
        out = Path(__file__).resolve().parent / out
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    video_rows = []
    warnings = []

    stats_df, stats_index, stats_warnings = load_statistics(root, args.statistics)
    warnings.extend(stats_warnings)
    summary = load_summary(root, args.summary)

    datasets = find_dataset_dirs(root)
    if not datasets:
        raise SystemExit(f'No DataSet* folders found under {root}')

    print(f'Data root: {root}')
    print(f'Datasets discovered: {len(datasets)} -> {", ".join(d.name for d in datasets)}')
    if stats_df is not None:
        print(f'statistics.csv: {len(stats_df):,} episode rows loaded')
    else:
        print('statistics.csv: not loaded')
    if summary:
        print('summary.csv: loaded for sanity checks')

    matched_stats_keys = set()
    videos_missing_stats = 0
    annotator_mismatches = 0
    missing_videos = 0

    for ds in datasets:
        ann_root = find_child_ci(ds, 'Annotations')
        vids_root = find_child_ci(ds, 'Videos') or find_child_ci(ds, 'videos')
        if not ann_root:
            warnings.append(f'{ds.name}: no Annotations folder')
            continue

        annotators = sorted([
            p for p in ann_root.iterdir()
            if p.is_dir() and p.name.lower().startswith('annotator')
        ])
        if not annotators:
            warnings.append(f'{ds.name}: no Annotator* folders')
            continue

        by_stem = defaultdict(list)
        for ad in annotators:
            for jp in ad.glob('*.json'):
                by_stem[jp.stem].append((ad.name, jp))

        video_index = {}
        if vids_root:
            for vp in vids_root.iterdir():
                if vp.is_file() and vp.suffix.lower() in VIDEO_EXTS:
                    video_index[vp.stem.lower()] = vp

        print(f'  {ds.name}: annotator folders={len(annotators)}, annotated videos={len(by_stem):,}, videos indexed={len(video_index):,}')

        for stem, anns in sorted(by_stem.items()):
            vp = video_index.get(stem.lower())
            if vp is None:
                missing_videos += 1
                if not args.allow_missing_video:
                    warnings.append(f'{ds.name}/{stem}: video missing, skipped')
                    continue

            loaded = []
            extras_all = {}
            for aname, jp in anns:
                try:
                    labels, extras = load_annotation(jp)
                    loaded.append((aname, labels))
                    extras_all[aname] = extras
                except Exception as e:
                    warnings.append(str(e))
            if not loaded:
                continue

            lengths = [len(x[1]) for x in loaded]
            n = min(lengths)
            if len(set(lengths)) > 1:
                warnings.append(f'{ds.name}/{stem}: annotation lengths {lengths}; using min={n}')

            meta = metadata_for_video(stats_index, ds.name, stem)
            stats_match = meta is not None
            if stats_match:
                matched_stats_keys.add((ds.name.lower(), stem.lower()))
            else:
                videos_missing_stats += 1

            expected = meta.get('num_annotators_expected') if meta else None
            found = len(loaded)
            annotator_count_matches = None if expected is None else int(found == expected)
            if expected is not None and found != expected:
                annotator_mismatches += 1
                warnings.append(
                    f'{ds.name}/{stem}: statistics.csv expects {expected} annotators; found {found}'
                )

            frame_consensus = []
            for i in range(n):
                washing = [int(labels[i].get('is_washing', 0)) for _, labels in loaded]
                codes_raw = [int(labels[i].get('code', 0)) for _, labels in loaded]
                # PSKUS class 7 (turn off faucet with paper towel) is not a WHO 1..6 technique.
                # AKAM's 7-class model is 0..6, so map 7 -> 0 while retaining raw votes.
                codes = [0 if c == 7 else c for c in codes_raw]
                wc, wv, wa = consensus(washing)
                cc, cv, ca = consensus(codes)
                frame_consensus.append((wc, wv, wa, cc, cv, ca, codes, codes_raw, washing))

            consensus_codes = [x[3] for x in frame_consensus]
            tmask = transition_mask(consensus_codes, args.transition_margin)
            split = deterministic_split(f'{ds.name}/{stem}')

            common_meta = {
                'statistics_match': int(stats_match),
                'statistics_location': meta.get('statistics_location') if meta else '',
                'num_annotators_expected': expected if expected is not None else '',
                'annotator_count_matches_statistics': annotator_count_matches if annotator_count_matches is not None else '',
                'total_duration_sec': meta.get('total_duration_sec') if meta else '',
                'ring': meta.get('ring') if meta and meta.get('ring') is not None else '',
                'armband': meta.get('armband') if meta and meta.get('armband') is not None else '',
                'long_nails': meta.get('long_nails') if meta and meta.get('long_nails') is not None else '',
            }

            for i, (wc, wv, wa, cc, cv, ca, codes, codes_raw, washing) in enumerate(frame_consensus):
                rows.append({
                    'dataset': ds.name,
                    'video_stem': stem,
                    'video_path': str(vp) if vp else '',
                    'frame_idx': i,
                    'split': split,
                    'num_annotators': found,
                    **common_meta,
                    'washing_consensus': int(wc),
                    'washing_votes': wv,
                    'washing_agreement': round(wa, 4),
                    'who_code': int(cc),
                    'who_votes': cv,
                    'who_agreement': round(ca, 4),
                    'who_transition': int(tmask[i]),
                    # Strict WHO hard target: washing consensus, at least two annotations,
                    # >=75% code agreement, >=2 agreeing votes, and away from transitions.
                    'who_valid_strict': int(
                        wc == 1 and found >= 2 and cv >= 2 and ca >= 0.75 and not tmask[i]
                    ),
                    'washing_votes_raw': '|'.join(map(str, washing)),
                    'who_votes_raw': '|'.join(map(str, codes_raw)),
                    'who_votes_mapped': '|'.join(map(str, codes)),
                })

            video_rows.append({
                'dataset': ds.name,
                'video_stem': stem,
                'video_path': str(vp) if vp else '',
                'split': split,
                'frames': n,
                'num_annotators': found,
                **common_meta,
            })

    if not rows:
        raise SystemExit('No manifest rows produced.')

    df = pd.DataFrame(rows)
    vdf = pd.DataFrame(video_rows)
    df.to_csv(out, index=False)
    vout = out.with_name(out.stem + '_videos.csv')
    vdf.to_csv(vout, index=False)

    # statistics.csv rows that did not map to an annotation/video entry
    stats_unmatched = 0
    if stats_index:
        stats_unmatched_keys = set(stats_index.keys()) - matched_stats_keys
        stats_unmatched = len(stats_unmatched_keys)
        if stats_unmatched:
            warnings.append(f'{stats_unmatched} statistics.csv rows did not match a processed annotated video')

    print('\n=== AKAM WHO v2 manifest summary ===')
    print(f'Wrote {len(df):,} frame rows -> {out}')
    print(f'Wrote {len(vdf):,} videos -> {vout}')
    print(f'Videos matched to statistics.csv: {int(vdf.statistics_match.sum()):,}/{len(vdf):,}')
    print(f'Videos missing statistics metadata: {videos_missing_stats:,}')
    print(f'Annotator-count mismatches vs statistics.csv: {annotator_mismatches:,}')
    print(f'Missing video files encountered: {missing_videos:,}')
    if stats_index:
        print(f'Unmatched statistics.csv rows: {stats_unmatched:,}')

    print('\nSplit counts (videos):')
    print(vdf['split'].value_counts().reindex(['train', 'val', 'test']).fillna(0).astype(int))

    print('\nAnnotator count distribution (videos):')
    print(vdf['num_annotators'].value_counts().sort_index())

    print('\nWHO strict usable frames:')
    print(df[df.who_valid_strict == 1].who_code.value_counts().sort_index().reindex(range(7), fill_value=0))

    print('\nWashing consensus:')
    print(df.washing_consensus.value_counts().sort_index())

    print('\nStatistics metadata coverage:')
    if stats_df is not None:
        print(f'  statistics rows loaded: {len(stats_df):,}')
        print(f'  processed videos matched: {int(vdf.statistics_match.sum()):,}')
        print(f'  ring known: {int((vdf.ring != "").sum()):,}')
        print(f'  armband known: {int((vdf.armband != "").sum()):,}')
        print(f'  long_nails known: {int((vdf.long_nails != "").sum()):,}')

    if summary:
        expected_episodes = summary.get('Total episodes')
        if expected_episodes is not None:
            try:
                expected_episodes = int(float(expected_episodes))
                print('\nsummary.csv sanity check:')
                print(f'  expected total episodes: {expected_episodes:,}')
                print(f'  processed annotated videos: {len(vdf):,}')
                if len(vdf) != expected_episodes:
                    print('  NOTE: counts differ; see warnings/unmatched statistics rows before preprocessing.')
            except (TypeError, ValueError):
                pass

    if warnings:
        wout = out.with_name(out.stem + '_warnings.txt')
        wout.write_text('\n'.join(warnings), encoding='utf-8')
        print(f'\nWarnings: {len(warnings):,} -> {wout}')
    else:
        print('\nWarnings: 0')

    print('\nIMPORTANT: frame labels come from annotator JSON consensus.')
    print('statistics.csv is used only for metadata and validation; malformed washing_duration is ignored.')


if __name__ == '__main__':
    main()
