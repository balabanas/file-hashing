# Create file with file sizes and hashes in the given folder and subfolders

# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import argparse
import hashlib
import os
import pickle
from pathlib import Path
import pandas as pd

LARGE_FILE_SIZE_THRESHOLD: int = 100_000


def get_hash(current_file: str) -> str:
    with open(current_file, 'rb') as file_obj:
        file_contents = file_obj.read()
        md5_hash = hashlib.md5(file_contents).hexdigest()
        # print(current_file, md5_hash)
        return md5_hash


def get_hash_with_chunks(current_file: str) -> str:
    with open(current_file, 'rb') as file_obj:
        md5_hash = hashlib.md5()
        while chunk := file_obj.read(LARGE_FILE_SIZE_THRESHOLD):
            md5_hash.update(chunk)
        return md5_hash.hexdigest()


def write_hashes(file_hashes: dict, args: argparse.Namespace) -> None:
    with open(args.savehashes, 'a', encoding='utf-8') as processed_files_csv:
        for key, value in file_hashes.items():
            try:
                processed_files_csv.write(f'{key}\t{value[0]}\t{value[1]}\n')
            except UnicodeEncodeError:
                print(f'{key}\t{value[0]}\t{value[1]}\n')
    file_hashes.clear()


def write_dirs(processed_dirs: dict, args:argparse.Namespace) -> None:
    with open(args.savedirs, 'wb') as outp:
        pickle.dump(processed_dirs, outp, pickle.HIGHEST_PROTOCOL)


def walk_files(dirs: dict, args: argparse.Namespace):
    file_hashes: dict = {}
    file_cnt: int = 0
    dirs_cnt: int = 0
    for current_dir, processed in dirs.items():
        if not processed:
            for f in list(filter(lambda x: os.path.isfile(os.path.join(current_dir, x)), os.listdir(current_dir))):
                current_file = os.path.join(current_dir, f)
                file_size = os.path.getsize(current_file)
                md5_hash = get_hash(current_file) if file_size < LARGE_FILE_SIZE_THRESHOLD else get_hash_with_chunks(current_file)
                file_hashes[current_file] = (file_size, md5_hash)
                file_cnt += 1
                if file_cnt % 100 == 0:
                    print(f"Files processed: {file_cnt}")
            dirs[current_dir] = True  # processed
            dirs_cnt += 1
            if len(file_hashes) > 5000:
                write_dirs(dirs, args)
                write_hashes(file_hashes, args)
    if file_hashes:
        write_dirs(dirs, args)
        write_hashes(file_hashes, args)
    df: pd.DataFrame = pd.DataFrame.from_dict(data=file_hashes, orient='index', columns=('size', 'hash'))
    df = df[df.duplicated('hash', keep=False)]
    df = df.sort_values('hash')
    print(df.head(100))


def main():
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--path', default='.', const='.', nargs='?', help='Path to folder to calculate hashes')
    parser.add_argument('--savedirs', default='processed_dirs.pkl', const='processed_dirs.pkl', nargs='?', help='Path to the file to save dirs')
    parser.add_argument('--savehashes', default='processed_files.csv', const='processed_files.csv', nargs='?', help='Path to the file to save hashes')
    args: argparse.Namespace = parser.parse_args()
    args.path = os.path.normpath(args.path)
    args.savedirs = os.path.normpath(args.savedirs)
    args.savehashes = os.path.normpath(args.savehashes)
    unprocessed_dirs = {key: value for key, value in update_dirs(args).items() if not value}
    walk_files(unprocessed_dirs, args)


def update_dirs(args: argparse.Namespace) -> dict:
    try:
        with open(args.savedirs, 'rb') as inp:
            processed_dirs: dict = pickle.load(inp)
    except FileNotFoundError:
        processed_dirs: dict = {args.path: False}
        with open(args.savehashes, 'w', encoding='utf-8') as processed_files_csv:
            processed_files_csv.write('path\tsize\thash\n')
    print(args.path)
    if args.path not in processed_dirs:
        processed_dirs[args.path] = False
    for root, dirs, _ in os.walk(args.path, topdown=False):
        for name in dirs:
            current_dir = os.path.join(root, name)
            if current_dir not in processed_dirs:
                processed_dirs[current_dir] = False
    with open(args.savedirs, 'wb') as outp:
        pickle.dump(processed_dirs, outp, pickle.HIGHEST_PROTOCOL)

    return processed_dirs


if __name__ == '__main__':
    main()
