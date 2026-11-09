"""Regenerate the six manuscript figure families from the packaged data."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import fontManager
import numpy as np

from reproduce import SEEDS, estimate, load_scores, read_csv


B = "#16738b"
C = "#b4561c"


def save(fig, output, name, lang):
    fig.savefig(output / f"{name}_{lang}.png", dpi=275)
    plt.close(fig)


def protocol(output, lang, tr):
    fig, (ax, lr) = plt.subplots(1, 2, figsize=(8.4, 3.2), layout="constrained")
    for row in read_csv("sensor_coordinates_mm.csv"):
        name = row["sensor"]
        x, y = float(row["x_mm"]), float(row["y_mm"])
        ax.scatter(x, y, facecolor=B if name in ("S2", "S3", "S5") else "white", edgecolor=B, s=45)
        ax.annotate(name, (x, y), xytext=(0, 7), ha="center", textcoords="offset points")
    ax.set(xlim=(-11.5, 11.5), ylim=(-11.5, 11.5), xlabel="x (mm)", ylabel="y (mm)",
           title=tr("(a) 节点布局", "(a) Sensor layout"))
    ax.set_aspect("equal")
    epoch = np.arange(1, 1501)
    rates = 3e-6 + .5*(3e-4 - 3e-6)*(1 + np.cos(np.pi*(epoch-1)/1499))
    lr.plot(epoch, rates, color=B)
    lr.set(yscale="log", xlabel=tr("完整训练轮", "Completed epoch"), ylabel=tr("学习率", "Learning rate"),
           title=tr("(b) 共同学习率", "(b) Shared learning rate"))
    save(fig, output, "Sparse_protocol", lang)


def layouts(output, lang, tr):
    order = ("S1/S2/S3/S4","S1/S4/S5","S2/S3/S5","S1/S4","S2/S3","S5")
    kinds = {
        "recurrent": (-.13, "o", B, tr("记忆", "Recurrent")),
        "framewise": (.13, "s", C, tr("逐帧", "Framewise")),
        "independent_recurrent": (.36, "D", "#754496", tr("独立 S5 重训", "Independent S5")),
    }
    fig, ax = plt.subplots(figsize=(8.4, 3.4), layout="constrained")
    seen = set()
    for row in read_csv("field_layout_scores.csv"):
        kind = row["model"]
        v = float(row["full_rmse_uT"])
        if kind == "five_node_shared_field":
            ax.axhline(v, ls="--", color="#45505a", label=tr("五点共享场参照", "Five-node shared-field reference"))
            continue
        offset, marker, color, label = kinds[kind]
        x = order.index(row["layout"]) + offset
        ax.scatter(x, v, marker=marker, color=color, label=label if kind not in seen else None)
        ax.annotate(f"{v:.2f}", (x,v), xytext=(0, 6), ha="center", fontsize=7, textcoords="offset points")
        seen.add(kind)
    ax.set_xticks(range(6), ("S1–S4", *order[1:]))
    ax.set(yscale="log", ylim=(3.4, 75), xlabel=tr("在线输入布局", "Online input layout"), ylabel="RMSE (µT)")
    ax.legend(frameon=False, ncol=2)
    save(fig, output, "Sparse_layouts", lang)


def effects(output, lang, tr, result):
    c = result["contrasts"]["B-A"]
    labs = tr(["总体","圆弧","半球","小平头","种子 101","种子 202","种子 303"],
              ["Overall","Rounded","Hemisphere","Small flat","Seed 101","Seed 202","Seed 303"])
    titles = tr(["均误变化 (mm)","P95 变化 (mm)","覆盖率变化 (百分点)"],
                ["Mean error change (mm)","P95 change (mm)","Coverage change (pp)"])
    fig, axes = plt.subplots(1, 3, sharey=True, figsize=(9.1, 3.2), layout="constrained")
    for j, ax in enumerate(axes):
        v = c["estimate"][j]
        lo, hi = c["interval"][j]
        domain = [c["domains"][k][j] for k in ("rounded","hemispherical","small_flat")]
        seeds = [x[j] for x in c["seed_effects"]]
        ax.axvline(0, ls="--", lw=.8, color="#526474")
        ax.errorbar(v, 0, xerr=[[v-lo],[hi-v]], fmt="D", capsize=3, color=B)
        ax.scatter(domain, [1,2,3], color=B)
        ax.scatter(seeds, [4,5,6], facecolor="white", edgecolor=B)
        ax.set_yticks(range(7), labs)
        ax.set_title(titles[j])
    axes[0].invert_yaxis()
    save(fig, output, "Paired_effects", lang)


def failure(output, lang, tr, result):
    fig, (a,b) = plt.subplots(1, 2, figsize=(8.7, 3.2), layout="constrained")
    a.axvspan(-.4,.4,color="#e4edf2")
    a.axvspan(2.6,3.4,color="#e4edf2")
    rows = read_csv("seed202_node_rmse.csv")
    for arm, color, marker, offset in (("B",B,"o",-.10),("C",C,"^",.10)):
        vals = [float(r["rmse_uT"]) for r in rows if r["arm"] == arm]
        a.scatter(np.arange(5)+offset, vals, color=color, marker=marker, label=arm)
    a.set_xticks(range(5), [f"S{i}" for i in range(1,6)])
    a.set(yscale="log", ylim=(.8,680), ylabel="RMSE (µT)", title=tr("(a) 节点磁场误差，种子 202", "(a) Field error by node, seed 202"))
    a.legend(frameon=False)
    values = [result["absolute"][k] for k in ("M","A","B","C")]
    colors = ["#45505a","#688393",B,C]
    b.bar(range(4), [v[5] for v in values], color=colors, width=.48, label=tr("接受且误差 ≤0.5 mm","Accepted with error ≤0.5 mm"))
    b.scatter(range(4), [v[2] for v in values], marker="s", facecolor="white", edgecolor=colors, label=tr("覆盖率","Accepted coverage"))
    b.set_xticks(range(4), [tr("五点实测","Measured"),"A","B","C"])
    b.set(ylim=(0,111),ylabel="%",title=tr("(b) 接受输出与有效精度","(b) Accepted output and spatial utility"))
    b.legend(frameon=False, fontsize=8)
    save(fig, output, "Failure_modes", lang)


def distribution(output, lang, tr, arrays, groups):
    fig, (a,b) = plt.subplots(1, 2, figsize=(8.6, 3.1), layout="constrained")
    weights = np.empty(97)
    for ix in groups.values():
        weights[ix] = 1/(len(groups)*len(ix))
    for k, color in zip("MABC", ("#45505a","#688393",B,C)):
        x = arrays["M"][:,0] if k=="M" else np.mean([arrays[f"{s}{k}"][:,0] for s in SEEDS], axis=0)
        idx = np.argsort(x)
        a.step(x[idx], np.cumsum(weights[idx]), where="post", color=color,
               label=tr("五点实测","Measured") if k=="M" else k, linestyle="--" if k=="M" else "-")
    a.set(xscale="log", xlabel=tr("逐序列原始均误 (mm)","Per-sequence raw mean error (mm)"),
          ylabel=tr("域等权累积分布","Equal-domain cumulative fraction"))
    a.legend(frameon=False,loc="lower right")
    delta = np.mean([arrays[f"{s}B"][:,1]-arrays[f"{s}A"][:,1] for s in SEEDS], axis=0)
    for j,k in enumerate(("rounded","hemispherical","small_flat")):
        x = np.sort(delta[groups[k]])
        b.scatter(x, j+np.linspace(-.23,.23,len(x)), s=9, color=B, alpha=.65)
        b.scatter(x.mean(),j,marker="D",color="#182f43")
    b.axvline(0,ls="--",lw=.8,color="#526474")
    b.set_yticks(range(3), tr(["圆弧","半球","小平头"], ["Rounded","Hemisphere","Small flat"]))
    b.invert_yaxis()
    b.set_xlabel(tr("逐序列 P95 变化 B−A (mm)","Per-sequence P95 difference B−A (mm)"))
    save(fig, output, "Sequence_distribution", lang)


def training(output, lang, tr):
    rows = read_csv("training_dev_samples.csv")
    fig, axes = plt.subplots(1,3,figsize=(9,3),sharey=True,layout="constrained")
    for j,(seed,ax) in enumerate(zip(SEEDS,axes)):
        for arm, color in (("B",B),("C",C)):
            a = [r for r in rows if int(r["seed"])==seed and r["arm"]==arm]
            for field, marker, label in (("train_mse","o","TRAIN"),("dev_mse","x","DEV")):
                ax.scatter([int(r["epoch"]) for r in a],[float(r[field]) for r in a],
                           s=9,alpha=.58,color=color,marker=marker,label=f"{arm} {label}" if j==0 else None)
        ax.set(yscale="log", xlim=(0,1530), xlabel=tr("完整训练轮","Completed epoch"), title=tr("种子 ","Seed ")+str(seed))
        ax.set_xticks([1,500,1000,1500])
    axes[0].set_ylabel(tr("共同 S235 归一化 MSE","Common S235 normalized MSE"))
    axes[0].legend(ncol=2,frameon=False,fontsize=8)
    save(fig, output, "Training_dev_samples", lang)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reproduced"))
    parser.add_argument("--lang", choices=("EN","ZH","both"), default="EN")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    arrays, counts, groups = load_scores()
    result = estimate(arrays, counts, groups)
    languages = ("EN","ZH") if args.lang=="both" else (args.lang,)
    available = {f.name for f in fontManager.ttflist}
    zh_font = next((n for n in ("Microsoft YaHei","Noto Sans CJK SC") if n in available), None)
    if "ZH" in languages and zh_font is None:
        parser.error("Rendering Chinese figures requires Microsoft YaHei or Noto Sans CJK SC")
    for lang in languages:
        def tr(zh, en):
            return zh if lang=="ZH" else en
        plt.rcParams.update({"font.family":tr(zh_font,"DejaVu Sans"),
                             "font.size":9, "axes.spines.top":False,"axes.spines.right":False})
        protocol(args.output,lang,tr)
        layouts(args.output,lang,tr)
        effects(args.output,lang,tr,result)
        failure(args.output,lang,tr,result)
        distribution(args.output,lang,tr,arrays,groups)
        training(args.output,lang,tr)
    print("Regenerated the six figure families.")


if __name__=="__main__":
    main()
