"""Generate black-and-white patent figures as editable SVG and PNG previews."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
import math
from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont


OUT = Path(__file__).resolve().parent
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"


@dataclass
class Style:
    width: int = 3
    dash: bool = False
    fill: str = "white"


class Canvas:
    def __init__(self, title: str, width: int = 1600, height: int = 1000):
        self.title = title
        self.width = width
        self.height = height
        self.img = Image.new("RGB", (width, height), "white")
        self.draw = ImageDraw.Draw(self.img)
        self.svg: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="white"/>',
            '<defs><marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="5" '
            'orient="auto" markerUnits="strokeWidth"><path d="M0,0 L10,5 L0,10 Z" fill="black"/></marker></defs>',
            '<style>text{font-family:"Noto Sans CJK SC","Noto Sans CJK",sans-serif;fill:black}</style>',
        ]
        self.text(width / 2, 42, title, 32, bold=True, anchor="mm")

    @staticmethod
    def _font(size: int, bold: bool = False):
        return ImageFont.truetype(FONT_BOLD if bold else FONT, size)

    def text(self, x: float, y: float, value: str, size: int = 24, *, bold: bool = False,
             anchor: str = "mm") -> None:
        font = self._font(size, bold)
        pil_anchor = {"mm": "mm", "lm": "lm", "rm": "rm", "la": "la"}.get(anchor, "mm")
        self.draw.text((x, y), value, font=font, fill="black", anchor=pil_anchor)
        svg_anchor = {"mm": "middle", "lm": "start", "rm": "end", "la": "start"}.get(anchor, "middle")
        weight = "700" if bold else "500"
        self.svg.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{svg_anchor}" dominant-baseline="middle">{escape(value)}</text>'
        )

    def multiline(self, x: float, y: float, lines: list[str] | tuple[str, ...], size: int = 22,
                  *, bold: bool = False, spacing: int = 1) -> None:
        step = size + spacing * 7
        start = y - step * (len(lines) - 1) / 2
        for i, line in enumerate(lines):
            self.text(x, start + i * step, line, size, bold=bold)

    def box(self, x: float, y: float, w: float, h: float, lines: list[str] | tuple[str, ...],
            *, ref: str | None = None, rounded: bool = True, dash: bool = False,
            fill: str = "white", size: int = 22, bold_first: bool = True) -> None:
        xy = (x, y, x + w, y + h)
        if rounded:
            self.draw.rounded_rectangle(xy, radius=20, fill=fill, outline="black", width=3)
            dash_attr = ' stroke-dasharray="12 8"' if dash else ""
            self.svg.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="{fill}" '
                f'stroke="black" stroke-width="3"{dash_attr}/>'
            )
        else:
            self.draw.rectangle(xy, fill=fill, outline="black", width=3)
            dash_attr = ' stroke-dasharray="12 8"' if dash else ""
            self.svg.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" '
                f'stroke="black" stroke-width="3"{dash_attr}/>'
            )
        if ref:
            self.text(x + 14, y + 16, ref, 20, bold=True, anchor="lm")
        step = size + 8
        start = y + h / 2 - step * (len(lines) - 1) / 2
        for i, line in enumerate(lines):
            self.text(x + w / 2, start + i * step, line, size, bold=(bold_first and i == 0))

    def ellipse(self, x: float, y: float, w: float, h: float, lines: list[str] | tuple[str, ...],
                *, ref: str | None = None, size: int = 22, dash: bool = False) -> None:
        self.draw.ellipse((x, y, x + w, y + h), fill="white", outline="black", width=3)
        dash_attr = ' stroke-dasharray="12 8"' if dash else ""
        self.svg.append(
            f'<ellipse cx="{x+w/2}" cy="{y+h/2}" rx="{w/2}" ry="{h/2}" fill="white" '
            f'stroke="black" stroke-width="3"{dash_attr}/>'
        )
        if ref:
            self.text(x + 22, y + 18, ref, 19, bold=True, anchor="lm")
        self.multiline(x + w / 2, y + h / 2, lines, size)

    def line(self, x1: float, y1: float, x2: float, y2: float, *, width: int = 3,
             dash: bool = False) -> None:
        if dash:
            segments = 20
            for i in range(segments):
                if i % 2 == 0:
                    a, b = i / segments, (i + 1) / segments
                    self.draw.line((x1 + (x2-x1)*a, y1 + (y2-y1)*a,
                                    x1 + (x2-x1)*b, y1 + (y2-y1)*b), fill="black", width=width)
        else:
            self.draw.line((x1, y1, x2, y2), fill="black", width=width)
        dash_attr = ' stroke-dasharray="12 8"' if dash else ""
        self.svg.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="black" '
            f'stroke-width="{width}"{dash_attr}/>'
        )

    def arrow(self, x1: float, y1: float, x2: float, y2: float, *, label: str | None = None,
              dash: bool = False, width: int = 3) -> None:
        self.line(x1, y1, x2, y2, width=width, dash=dash)
        dash_attr = 'stroke-dasharray="12 8" ' if dash else ""
        angle = math.atan2(y2-y1, x2-x1)
        length, spread = 20, 10
        p1 = (x2, y2)
        p2 = (x2-length*math.cos(angle)+spread*math.sin(angle),
              y2-length*math.sin(angle)-spread*math.cos(angle))
        p3 = (x2-length*math.cos(angle)-spread*math.sin(angle),
              y2-length*math.sin(angle)+spread*math.cos(angle))
        self.draw.polygon([p1, p2, p3], fill="black")
        self.svg.append(
            f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="black" stroke-width="{width}" '
            f'{dash_attr}marker-end="url(#arrow)"/>'
        )
        if label:
            self.text((x1+x2)/2, (y1+y2)/2-18, label, 19)

    def brace_label(self, x: float, y: float, value: str, size: int = 19) -> None:
        self.text(x, y, value, size, anchor="lm")

    def save(self, stem: str) -> None:
        self.svg.append(f'<text x="{self.width/2}" y="{self.height-25}" font-size="22" '
                        f'text-anchor="middle">{escape(self.title.split("：",1)[0])}</text>')
        self.svg.append("</svg>")
        (OUT / f"{stem}.svg").write_text("\n".join(self.svg), encoding="utf-8")
        self.img.save(OUT / f"{stem}.png", optimize=True)


def fig1() -> None:
    c = Canvas("图1：仿真—实机双向闭环总体架构")
    nodes = [
        (110, 120, ["仿真任务与", "脚本专家"], "110"),
        (440, 120, ["实机同构", "数据生成"], "120"),
        (770, 120, ["统一校验与", "策略训练"], "130"),
        (1100, 120, ["真实机器人", "策略执行"], "140"),
        (1100, 600, ["实机多模态采集", "Actual / Target / 图像"], "150"),
        (770, 600, ["因果同步与", "公共语义映射"], "160"),
        (440, 600, ["数字孪生验证", "实体 / 虚影 / 双模式"], "170"),
        (110, 600, ["误差分析与", "参数修正"], "180"),
    ]
    for x, y, lines, ref in nodes:
        c.box(x, y, 280, 150, lines, ref=ref, size=23)
    for a, b in zip(nodes[:4], nodes[1:4]):
        c.arrow(a[0]+280, a[1]+75, b[0], b[1]+75)
    c.arrow(1240, 270, 1240, 600)
    for a, b in zip(nodes[4:], nodes[5:]):
        c.arrow(a[0], a[1]+75, b[0]+280, b[1]+75)
    c.arrow(110, 675, 60, 675)
    c.arrow(60, 675, 60, 195)
    c.arrow(60, 195, 110, 195, label="闭环更新")
    c.box(480, 355, 640, 120, ["双向关系核心", "Sim→Real 数据同构  +  Real→Sim 数字孪生"], ref="100", size=25)
    c.save("fig01_overall_loop")


def fig2() -> None:
    c = Canvas("图2：多源数据公共时间区间与因果重采样")
    c.box(60, 105, 270, 110, ["Actual状态流", "非均匀采样"], ref="210")
    c.box(60, 285, 270, 110, ["Target指令流", "异步阶跃更新"], ref="220")
    c.box(60, 465, 270, 110, ["多相机图像流", "异步时间戳"], ref="230")
    c.box(420, 220, 300, 180, ["公共有效区间", "Tstart=max(首时间)", "Tend=min(末时间)"], ref="240")
    for y in (160, 340, 520):
        c.arrow(330, y, 420, 310)
    c.box(805, 105, 300, 110, ["线性插值", "连续Actual"], ref="251")
    c.box(805, 285, 300, 110, ["零阶保持", "不读取未来Target"], ref="252")
    c.box(805, 465, 300, 110, ["时间最近邻", "相机帧"], ref="253")
    for y in (160, 340, 520):
        c.arrow(720, 310, 805, y)
    c.box(1200, 220, 330, 180, ["统一采样网格", "Actual + Target + 图像", "同一帧语义"], ref="260", size=23)
    for y in (160, 340, 520):
        c.arrow(1105, y, 1200, 310)
    c.line(170, 720, 1430, 720, width=3)
    for i in range(9):
        x = 230 + i * 140
        c.line(x, 705, x, 735, width=2)
        c.text(x, 760, f"t{i}", 18)
    c.text(800, 670, "统一时间网格（示意）", 22, bold=True)
    c.box(475, 815, 650, 95, ["因果约束：时刻 ti 的Target仅来自 timestamp ≤ ti 的指令"], ref="270", size=21)
    c.save("fig02_causal_sync")


def fig3() -> None:
    c = Canvas("图3：关节、夹爪与相机的公共语义映射")
    c.text(230, 100, "数据源语义", 25, bold=True)
    c.text(800, 100, "公共语义层 300", 25, bold=True)
    c.text(1370, 100, "模型/工具链语义", 25, bold=True)
    left = [
        (150, ["左/右臂各7关节", "单位可能不同"], "311"),
        (355, ["夹爪原始编码", "0闭合/负值张开等"], "312"),
        (560, ["head / wrist_left", "wrist_right"], "313"),
    ]
    middle = [
        (150, ["16维公共状态", "左7+夹爪+右7+夹爪"], "321"),
        (355, ["夹爪物理开度", "0闭合，最大值张开"], "322"),
        (560, ["front / left_wrist", "right_wrist"], "323"),
    ]
    right = [
        (150, ["仿真qpos / 实机obs", "统一关节顺序与弧度"], "331"),
        (355, ["控制器与数据集", "统一长度单位"], "332"),
        (560, ["模型固定图像键", "三相机有效性mask"], "333"),
    ]
    for y, lines, ref in left:
        c.box(60, y, 340, 135, lines, ref=ref)
    for y, lines, ref in middle:
        c.box(630, y, 340, 135, lines, ref=ref)
    for y, lines, ref in right:
        c.box(1200, y, 340, 135, lines, ref=ref)
    for y in (217, 422, 627):
        c.arrow(400, y, 630, y, label="映射/归一化")
        c.arrow(970, y, 1200, y, label="统一输出")
    c.box(470, 790, 660, 105, ["映射元数据：来源类型、夹爪编码、相机映射、单位和版本"], ref="340", size=22)
    c.save("fig03_semantic_mapping")


def fig4() -> None:
    c = Canvas("图4：仿真数据转换为实机同构数据结构")
    c.box(60, 130, 300, 185, ["仿真轨迹", "state / qvel / qtorque", "joint_target / 三相机", "sim_time + wall_start"], ref="410", size=20)
    c.box(470, 130, 330, 185, ["同构转换模块", "时间戳换算", "夹爪编码转换", "相机名称映射"], ref="420", size=21)
    c.arrow(360, 222, 470, 222)
    c.box(920, 95, 610, 570, [""], ref="430", bold_first=False, size=24)
    c.text(1225, 135, "实机兼容数据集", 25, bold=True)
    tree = [
        "metadata.yaml",
        "episodes/<id>/",
        "  obs/arms/left/state.parquet",
        "  obs/arms/right/state.parquet",
        "  action/arms/left/qpos.parquet",
        "  action/arms/right/qpos.parquet",
        "  cameras/head/<ns>.jpeg",
        "  cameras/wrist_left/<ns>.jpeg",
        "  cameras/wrist_right/<ns>.jpeg",
    ]
    for i, line in enumerate(tree):
        c.text(975, 190 + i * 46, line, 21, anchor="lm", bold=(i < 2))
    c.arrow(800, 222, 920, 222)
    c.box(260, 500, 520, 125, ["绝对时间戳", "wall_start_ns + round((t-t0)×10^9)"], ref="440", size=22)
    c.arrow(520, 500, 620, 315, dash=True)
    c.box(510, 755, 580, 115, ["同一读取器 / 厂商校验器 / 训练工具链", "无需区分sim与real字段结构"], ref="450", size=23)
    c.arrow(1225, 665, 1090, 812)
    c.save("fig04_isomorphic_dataset")


def fig5() -> None:
    c = Canvas("图5：Actual实体与Target非物理虚影")
    c.box(60, 140, 300, 135, ["实机观测Actual", "实测关节与夹爪"], ref="510")
    c.box(60, 560, 300, 135, ["控制指令Target", "命令关节与夹爪"], ref="520")
    c.box(480, 110, 360, 190, ["第一状态数据", "Actual权威实体", "参与实体场景构建"], ref="530", size=23)
    c.box(480, 530, 360, 190, ["第二独立状态数据", "Target正运动学", "不执行物理积分"], ref="540", dash=True, size=23)
    c.arrow(360, 207, 480, 207)
    c.arrow(360, 627, 480, 627)
    c.box(1010, 105, 480, 210, ["数字孪生实体机器人", "由Actual驱动", "碰撞 / 接触 / 动力学"], ref="550", size=24)
    c.box(1010, 525, 480, 210, ["半透明Target虚影", "仅追加可视几何", "不参与碰撞 / 接触 / 动力学"], ref="560", dash=True, size=23)
    c.arrow(840, 205, 1010, 205)
    c.arrow(840, 625, 1010, 625)
    c.line(930, 500, 930, 780, dash=True)
    c.text(930, 810, "物理隔离边界 570", 21, bold=True)
    c.arrow(1250, 525, 1250, 315, label="同场景叠加", dash=True)
    c.box(520, 825, 560, 90, ["共享同一机器人模型定义，状态数据彼此独立"], ref="580", size=21)
    c.save("fig05_actual_target_ghost")


def fig6() -> None:
    c = Canvas("图6：运动学/动力学双模式及误差分离")
    c.box(590, 90, 420, 110, ["统一EpisodeData", "Actual + 可选Target"], ref="610", size=23)
    c.arrow(800, 200, 400, 320)
    c.arrow(800, 200, 1200, 320)
    c.box(125, 320, 550, 145, ["运动学模式 620", "Actual直接写qpos → 正运动学", "精确复现实测姿态"], size=23)
    c.box(925, 320, 550, 145, ["动力学模式 630", "Target → 控制器 → 物理积分", "得到仿真实际状态"], size=23)
    c.box(125, 560, 550, 155, ["检查映射与视觉一致性", "关节顺序 / 零位 / 夹爪编码", "相机外参 / 时间同步"], ref="640", size=21)
    c.box(925, 560, 550, 155, ["检查控制与模型一致性", "跟踪延迟 / 饱和 / 摩擦 / 负载", "质量 / 惯量 / 阻尼 / 控制增益"], ref="650", size=21)
    c.arrow(400, 465, 400, 560)
    c.arrow(1200, 465, 1200, 560)
    c.box(460, 805, 680, 105, ["误差分类结果 660", "映射误差｜控制误差｜动力学建模误差｜视觉域差异"], size=22)
    c.arrow(400, 715, 650, 805)
    c.arrow(1200, 715, 950, 805)
    c.save("fig06_dual_modes")


def fig7() -> None:
    c = Canvas("图7：多相机同帧对比与误差诊断界面")
    c.box(55, 90, 1490, 805, [""], ref="700", rounded=False, bold_first=False)
    c.box(85, 120, 1430, 80, ["数据源｜episode｜播放/暂停｜模式｜速度｜Target虚影"], ref="710", rounded=False, size=21)
    c.box(85, 225, 700, 270, ["交互式数字孪生自由视角", "Actual实体 + Target半透明虚影"], ref="720", rounded=False, size=25)
    c.box(815, 225, 215, 125, ["仿真front"], ref="731", rounded=False, size=20)
    c.box(1055, 225, 215, 125, ["仿真left wrist"], ref="732", rounded=False, size=18)
    c.box(1295, 225, 215, 125, ["仿真right wrist"], ref="733", rounded=False, size=18)
    c.box(815, 370, 215, 125, ["实机head"], ref="741", rounded=False, size=20)
    c.box(1055, 370, 215, 125, ["实机wrist left"], ref="742", rounded=False, size=18)
    c.box(1295, 370, 215, 125, ["实机wrist right"], ref="743", rounded=False, size=18)
    c.box(85, 530, 700, 160, ["16通道Target / Actual数值表", "误差阈值超限标记"], ref="750", rounded=False, size=23)
    c.box(815, 530, 695, 160, ["16通道滚动趋势图", "Target、Actual及误差随时间变化"], ref="760", rounded=False, size=23)
    c.box(85, 725, 1425, 130, ["帧级诊断结果 770", "关节误差｜夹爪误差｜模型限位｜相机对齐｜数据来源｜任务状态"], rounded=False, size=22)
    c.save("fig07_multimodal_dashboard")


def fig8() -> None:
    c = Canvas("图8：实时镜像的线程隔离与最新帧通信结构")
    c.box(75, 110, 650, 690, [""], ref="810", rounded=False, bold_first=False)
    c.text(400, 145, "网络事件循环", 27, bold=True)
    c.box(135, 210, 530, 115, ["Web / WebSocket服务", "客户端命令与状态广播"], ref="811")
    c.box(135, 375, 530, 95, ["线程安全命令队列"], ref="812")
    c.box(135, 515, 530, 95, ["最新帧槽（覆盖旧帧）"], ref="813")
    c.box(135, 655, 530, 95, ["多个浏览器客户端", "慢客户端丢帧但不阻塞"], ref="814", size=21)
    c.arrow(300, 325, 300, 375)
    c.line(135, 562, 110, 562)
    c.line(110, 562, 110, 270)
    c.arrow(110, 270, 135, 270)
    c.arrow(400, 655, 400, 610)
    c.box(875, 110, 650, 690, [""], ref="820", rounded=False, bold_first=False)
    c.text(1200, 145, "专用仿真线程", 27, bold=True)
    c.box(935, 210, 530, 115, ["数据源适配", "离线episode / 实时Actual与Target"], ref="821")
    c.box(935, 390, 530, 135, ["数字孪生步进", "命令处理 / 运动学或动力学", "Actual实体 / Target虚影"], ref="822", size=21)
    c.box(935, 610, 530, 125, ["MuJoCo模型与离屏渲染", "图形上下文线程局部"], ref="823")
    c.arrow(1200, 325, 1200, 390)
    c.arrow(1200, 525, 1200, 610)
    c.arrow(665, 422, 935, 422, label="控制命令")
    c.arrow(935, 562, 665, 562, label="最新帧")
    c.box(480, 855, 640, 75, ["线程边界 830：模型、数据、控制器和渲染器同线程创建与使用"], size=20)
    c.save("fig08_thread_architecture")


def fig9() -> None:
    c = Canvas("图9：基于仿真—实机差异的迭代修正闭环")
    items = [
        (100, 150, ["仿真数据生成", "域随机化"], "910"),
        (500, 90, ["统一策略训练", "与离线评测"], "920"),
        (1000, 150, ["实机策略执行", "多模态采集"], "930"),
        (1080, 560, ["Reality-to-Sim", "数字孪生回放"], "940"),
        (520, 700, ["差异分析", "分类与阈值判定"], "950"),
        (80, 560, ["参数修正", "数据筛选"], "960"),
    ]
    sizes = [(320,140),(350,140),(350,140),(350,140),(430,140),(350,140)]
    for (x,y,lines,ref),(w,h) in zip(items,sizes):
        c.box(x,y,w,h,lines,ref=ref,size=23)
    c.arrow(420, 200, 500, 160)
    c.arrow(850, 160, 1000, 200)
    c.arrow(1175, 290, 1255, 560)
    c.arrow(1080, 630, 950, 770)
    c.arrow(520, 770, 430, 630)
    c.arrow(255, 560, 260, 290)
    c.box(585, 390, 430, 155, ["误差信息 970", "控制跟踪 / 动力学模型", "视觉域 / 时间同步 / 数据质量"], size=21)
    c.arrow(1080, 630, 1015, 468, dash=True)
    c.arrow(735, 700, 800, 545, dash=True)
    c.box(475, 865, 650, 75, ["输出：仿真参数、控制参数、相机参数及训练配置的更新量"], ref="980", size=20)
    c.save("fig09_feedback_loop")


def main() -> None:
    for fn in (fig1, fig2, fig3, fig4, fig5, fig6, fig7, fig8, fig9):
        fn()
    print(f"generated 9 SVG and 9 PNG files in {OUT}")


if __name__ == "__main__":
    main()
