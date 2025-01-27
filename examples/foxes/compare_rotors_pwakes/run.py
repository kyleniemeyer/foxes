import numpy as np
import pandas as pd
import argparse
import matplotlib.pyplot as plt

import foxes
import foxes.variables as FV
import foxes.constants as FC
from foxes.utils.runners import DaskRunner

def calc(args, rotor, sdata, pwake, cks):
    mbook = foxes.models.ModelBook()
    ttype = foxes.models.turbine_types.PCtFile(args.turbine_file)
    mbook.turbine_types[ttype.name] = ttype
    D = ttype.D

    farm = foxes.WindFarm()
    farm.add_turbine(
        foxes.Turbine(
            xy=np.array([0.0, 0.0]), turbine_models=args.tmodels + [ttype.name]
        ),
        verbosity=0,
    )
    farm.add_turbine(
        foxes.Turbine(
            xy=np.array([args.dist_x, 0.0]),
            turbine_models=["sety"] + args.tmodels + [ttype.name],
        ),
        verbosity=0,
    )

    states = foxes.input.states.StatesTable(
        sdata,
        output_vars=[FV.WS, FV.WD, FV.TI, FV.RHO],
        var2col={FV.WS: "ws", FV.WD: "wd", FV.TI: "ti", FV.RHO: "rho"},
    )

    ydata = np.full((len(sdata.index), farm.n_turbines), np.nan)
    ydata[:, 1] = sdata["y"].to_numpy()
    mbook.turbine_models["sety"] = foxes.models.turbine_models.SetFarmVars(
        pre_rotor=True
    )
    mbook.turbine_models["sety"].add_var(FV.Y, ydata)

    algo = foxes.algorithms.Downwind(
        mbook,
        farm,
        states=states,
        rotor_model=rotor,
        wake_models=args.wakes,
        wake_frame="rotor_wd",
        partial_wakes_model=pwake,
        chunks=cks,
        verbosity=0,
    )

    print(f"\nCalculating rotor = {rotor}, pwake = {pwake}")
    farm_results = algo.calc_farm()

    return farm_results, D


def run_foxes(args):
    cks = None if args.nodask else {FC.STATE: args.chunksize}

    ws = args.ws
    var = args.var
    swks = ", ".join(args.wakes)
    ttl0 = f"ws$_0$ = {ws} m, ti$_0$ = {args.ti}"

    varn = 1
    vlab = var
    if var in [FV.WS, FV.REWS, FV.REWS2, FV.REWS3]:
        varn = ws
        vlab = f"{var}/ws$_0$"

    Ny = int((args.ymax - args.ymin) // args.ystep)
    sdata = pd.DataFrame(index=range(Ny + 1))
    sdata.index.name = "state"
    sdata["ws"] = args.ws
    sdata["wd"] = args.wd
    sdata["ti"] = args.ti
    sdata["rho"] = args.rho
    sdata["y"] = np.linspace(args.ymin, args.ymax, Ny + 1)

    fig, ax = plt.subplots(figsize=(10, 4))
    if len(args.rotors) == 1:
        for pwake in args.pwakes:
            farm_results, D = calc(args, args.rotors[0], sdata, pwake, cks)

            ax.plot(
                farm_results[FV.Y][:, 1] / D,
                farm_results[var][:, 1] / varn,
                linewidth=2,
                alpha=0.6,
                label=pwake,
            )

            title = f"{swks}, variable {var}\nVarying partial wake models, {ttl0}, rotor = {args.rotors[0]}"

    elif len(args.pwakes) == 1:
        for rotor in args.rotors:
            farm_results, D = calc(args, rotor, sdata, args.pwakes[0], cks)

            ax.plot(
                farm_results[FV.Y][:, 1] / D,
                farm_results[var][:, 1] / varn,
                linewidth=2,
                alpha=0.6,
                label=rotor,
            )

            title = f"{swks}, variable {var}\nVarying rotor models, {ttl0}, pwake = {args.pwakes[0]}"

    elif len(args.rotors) == len(args.pwakes):
        for rotor, pwake in zip(args.rotors, args.pwakes):
            farm_results, D = calc(args, rotor, sdata, pwake, cks)

            ax.plot(
                farm_results[FV.Y][:, 1] / D,
                farm_results[var][:, 1] / varn,
                linewidth=2,
                alpha=0.6,
                label=f"{rotor}, {pwake}",
            )

            title = (
                "{swks}, variable {var}\nVarying rotor and partial wake models, {ttl0}"
            )

    else:
        raise ValueError(
            f"Please either give one rotor, or one pwake, or same number of both"
        )

    if args.title is not None:
        title = args.title

    ax.set_title(title)
    ax.set_xlabel("y/D")
    ax.set_ylabel(vlab)
    ax.legend()
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ws", help="The wind speed", type=float, default=9.0)
    parser.add_argument("--wd", help="The wind direction", type=float, default=270.0)
    parser.add_argument("--ti", help="The TI value", type=float, default=0.08)
    parser.add_argument("--rho", help="The air density", type=float, default=1.225)
    parser.add_argument(
        "-t",
        "--turbine_file",
        help="The P-ct-curve csv file (path or static)",
        default="NREL-5MW-D126-H90.csv",
    )
    parser.add_argument("-v", "--var", help="The variable selection", default=FV.REWS)
    parser.add_argument(
        "-d", "--dist_x", help="The turbine distance in x", type=float, default=500.0
    )
    parser.add_argument(
        "-y0", "--ymin", help="The minimal y value", type=float, default=-500.0
    )
    parser.add_argument(
        "-y1", "--ymax", help="The maximal y value", type=float, default=500.0
    )
    parser.add_argument(
        "-ys", "--ystep", help="The step size in y direction", type=float, default=1.0
    )
    parser.add_argument(
        "-w",
        "--wakes",
        help="The wake models",
        default=["Bastankhah_linear_k002"],
        nargs="+",
    )
    parser.add_argument(
        "-m", "--tmodels", help="The turbine models", default=["kTI_02"], nargs="+"
    )
    parser.add_argument(
        "-r", "--rotors", help="The rotor model(s)", default=["grid100"], nargs="+"
    )
    parser.add_argument(
        "-p",
        "--pwakes",
        help="The partial wakes model(s)",
        default=["distsliced9", "axiwake6", "rotor_points"],
        nargs="+",
    )
    parser.add_argument("-tt", "--title", help="The figure title", default=None)
    parser.add_argument(
        "-c", "--chunksize", help="The maximal chunk size", type=int, default=1000
    )
    parser.add_argument("-sc", "--scheduler", help="The scheduler choice", default=None)
    parser.add_argument(
        "-n",
        "--n_workers",
        help="The number of workers for distributed run",
        type=int,
        default=None,
    )
    parser.add_argument(
        "-tw",
        "--threads_per_worker",
        help="The number of threads per worker for distributed run",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--nodask", help="Use numpy arrays instead of dask arrays", action="store_true"
    )
    args = parser.parse_args()

    with DaskRunner(
        scheduler=args.scheduler,
        n_workers=args.n_workers,
        threads_per_worker=args.threads_per_worker,
    ) as runner:
        runner.run(run_foxes, args=(args,))
