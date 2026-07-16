"""Command-line entry point: `phoqupy demo`, `phoqupy --version`."""
import argparse
import sys


def main(argv=None):
    p = argparse.ArgumentParser(prog="phoqupy", description="PhoQuPy quantum-optics automation.")
    p.add_argument("--version", action="store_true", help="print version and exit")
    sub = p.add_subparsers(dest="cmd")
    d = sub.add_parser("demo", help="run a simulated experiment and save a figure")
    d.add_argument("experiment", nargs="?", default="confocal",
                   choices=["confocal", "cryo", "hbt", "fiber", "stitch", "hyper"])
    d.add_argument("-o", "--out", default=None, help="save figure to this path")
    args = p.parse_args(argv)

    import phoqupy
    if args.version:
        print(f"phoqupy {phoqupy.__version__}"); return 0
    if args.cmd != "demo":
        p.print_help(); return 0

    import matplotlib
    if args.out:
        matplotlib.use("Agg")
    e = args.experiment
    out = args.out
    if e == "confocal":
        m = phoqupy.ConfocalScan(step=1.0, simulate=True).run()
        print("PL map:", m.matrix.shape, "brightest pixel:", m.pick_brightest())
        m.plot_map(savepath=out) if out else m.plot_map()
    elif e == "cryo":
        m = phoqupy.CryoScan(step=1.0, simulate=True).run()
        print("Cryo PL map:", m.matrix.shape); m.plot_map(savepath=out) if out else m.plot_map()
    elif e == "hbt":
        h = phoqupy.HBTMeasurement(simulate=True)
        tau, g2 = h.g2(); print("g2(0) ~", round(float(g2.min()), 3))
        h.plot_g2(savepath=out) if out else h.plot_g2()
    elif e == "fiber":
        f = phoqupy.FiberAlignment(simulate=True); f.run()
        print("optimum (Y,Z) V:", tuple(round(v, 1) for v in f.optimum()))
        f.plot(savepath=out) if out else f.plot()
    elif e == "stitch":
        s = phoqupy.StitchedScan(grid=(6, 6), simulate=True).run(); s.stitch()
        print("mosaic:", s.mosaic.shape); s.plot(savepath=out) if out else s.plot()
    elif e == "hyper":
        hs = phoqupy.HyperspectralScan(simulate=True).run()
        print("cube:", hs.cube.shape); hs.plot(savepath=out) if out else hs.plot()
    if out:
        print("saved:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
