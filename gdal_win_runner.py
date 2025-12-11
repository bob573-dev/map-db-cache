import sys
import subprocess

from gdal_runner import prepare_gdal_env


def main():
    if len(sys.argv) < 2:
        print("Usage: gdal_runner <command> [args...]")
        sys.exit(1)

    env, bin_dir = prepare_gdal_env(win=True)

    gdal_cmd = sys.argv[1]
    gdal_args = sys.argv[2:]
    result = subprocess.run([str(bin_dir / gdal_cmd)] + gdal_args, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
