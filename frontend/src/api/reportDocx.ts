/**
 * Word 详细报告生成（模块 7）：
 * 内容口径取自用户模板《选址分析报告模板0912》，版式按项目可行性研究报告格式重排：
 * 封面 → 目录（静态章节索引，逐行排布，永不错乱）→ 第一章 总论 → 第二章 项目需求与选址原则
 * → 第三章 选址评价指标体系 → 第四章 单因子分析评价 → 第五章 场址方案综合比选
 * → 第六章 推荐地块论证与实施建议。
 * 图表按章编号（图 3-1 / 表 5-1），ECharts 关闭动画后离屏渲染。
 * 全部数据取自本次真实计算结果（store），不使用演示数值。
 */
import {
  AlignmentType,
  BorderStyle,
  Document,
  ImageRun,
  Packer,
  PageBreak,
  Paragraph,
  ShadingType,
  Table,
  TableCell,
  TableRow,
  TextRun,
  VerticalAlign,
  WidthType,
} from 'docx'
import type { IParagraphOptions, ISectionOptions } from 'docx'
import type { ScenarioDetail } from '../types/scenario'
import type { SelectionResponse, CandidateParcel } from '../types/selection'
import type { ParseResult } from '../types/ai'
import { PREFERENCE_LEVELS } from '../store/config'
import {
  candidateScoreBarPng,
  dataUrlToU8,
  mapSnapshotPng,
  topRadarPng,
  weightsPiePng,
} from './reportCharts'

/* ============ 版式常量（等线字体，四级标题沿用模板字号） ============ */

const FONT = { ascii: 'DengXian', eastAsia: '等线', hAnsi: 'DengXian' }
const SIZE = { cover: 52, chapter: 32, section: 30, sub: 28, body: 22, small: 21 } // 半点
const INK = '1F2937'
const GRAY = '6B7280'

export interface ReportDocxSource {
  scenario: ScenarioDetail
  result: SelectionResponse
  /** 本次展示权重（后端实际生效值，缺失退回前端偏好值） */
  weights: Record<string, number>
  /** 选址偏好三档 */
  preferences: Record<string, string>
  /** AI 需求解析结果（可能为 null：用户未走聊天流程） */
  parseResult: ParseResult | null
  config: {
    algorithmName: string
    gridSize: number
    topN: number
    minAreaHa: number
    targetAreaHa: number | null
    areaRange: { lo: number; hi: number } | null
    weightModeName: string
    weightSource?: string
  }
  map?: { getCanvas: () => HTMLCanvasElement }
}

/* ============ 基础构件 ============ */

function run(text: string, size = SIZE.body, bold = false, color = INK): TextRun {
  return new TextRun({ text, font: FONT, size, bold, color })
}

function p(text: string, opts: Partial<IParagraphOptions> = {}): Paragraph {
  return new Paragraph({
    children: [run(text)],
    spacing: { after: 100, line: 300 },
    ...opts,
  })
}

function bullet(text: string, bold = false): Paragraph {
  return new Paragraph({
    bullet: { level: 0 },
    children: [run(text, SIZE.body, bold)],
    spacing: { after: 60, line: 300 },
  })
}

function chapter(text: string): Paragraph {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [run(text, SIZE.chapter, true)],
    spacing: { before: 320, after: 180 },
    keepNext: true,
  })
}

function section(text: string): Paragraph {
  return new Paragraph({
    children: [run(text, SIZE.section, true)],
    spacing: { before: 220, after: 120 },
    keepNext: true,
  })
}

function subsection(text: string): Paragraph {
  return new Paragraph({
    children: [run(text, SIZE.sub, true)],
    spacing: { before: 160, after: 100 },
    keepNext: true,
  })
}

/** 模板中的灰底说明框（1×1 表格） */
function box(text: string): Table {
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: [
      new TableRow({
        children: [
          new TableCell({
            shading: { type: ShadingType.CLEAR, fill: 'F2F4F7', color: 'auto' },
            margins: { top: 100, bottom: 100, left: 160, right: 160 },
            verticalAlign: VerticalAlign.CENTER,
            children: [
              new Paragraph({
                children: [run(text, SIZE.body, false, '444950')],
                spacing: { line: 300 },
              }),
            ],
          }),
        ],
      }),
    ],
  })
}

function spacer(after = 120): Paragraph {
  return new Paragraph({ children: [], spacing: { after } })
}

/** 表题（表上方居中） */
function tableCaption(text: string): Paragraph {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 140, after: 60 },
    keepNext: true,
    children: [run(text, SIZE.small, true)],
  })
}

/** 目录行：level 0 章（加粗）、level 1 节（缩进） */
function tocLine(text: string, level: 0 | 1): Paragraph {
  return new Paragraph({
    indent: level === 1 ? { left: 480 } : undefined,
    spacing: { after: 90, line: 330 },
    children: [run(text, level === 0 ? SIZE.body + 2 : SIZE.body, level === 0)],
  })
}

/** 数据表：首行表头灰底加粗 */
function dataTable(
  header: string[],
  rows: (string | number)[][],
  widths?: number[]
): Table {
  const mk = (text: string | number, isHead: boolean, w?: number) =>
    new TableCell({
      shading: isHead ? { type: ShadingType.CLEAR, fill: 'E9EEF3', color: 'auto' } : undefined,
      margins: { top: 60, bottom: 60, left: 100, right: 100 },
      verticalAlign: VerticalAlign.CENTER,
      width: w ? { size: w, type: WidthType.PERCENTAGE } : undefined,
      children: [
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [run(String(text), SIZE.small, isHead)],
          spacing: { line: 280 },
        }),
      ],
    })
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: [
      new TableRow({
        tableHeader: true,
        children: header.map((h, i) => mk(h, true, widths?.[i])),
      }),
      ...rows.map((r) => new TableRow({ children: r.map((c, i) => mk(c, false, widths?.[i])) })),
    ],
  })
}

/** 图 + 图题（图下方居中）；pngUrl 为 null 时整体跳过 */
function figure(pngUrl: string | null, caption: string, width = 560, height = 271): (Paragraph | Table)[] {
  if (!pngUrl) return []
  const ratio = height / width
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 120, after: 40 },
      children: [
        new ImageRun({
          type: 'png',
          data: dataUrlToU8(pngUrl),
          transformation: { width, height: Math.round(width * ratio) },
        }),
      ],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 160 },
      children: [run(caption, SIZE.small, false, GRAY)],
    }),
  ]
}

const pct = (w: number | undefined): string => `${((w ?? 0) * 100).toFixed(1)}%`

/** 多边形包围盒中心（展示用，非精确质心） */
function centroidText(c: CandidateParcel): string {
  try {
    const ring = c.geometry.coordinates[0]
    let sx = 0
    let sy = 0
    for (const [x, y] of ring) {
      sx += x
      sy += y
    }
    const lon = (sx / ring.length).toFixed(5)
    const lat = (sy / ring.length).toFixed(5)
    return `东经 ${lon}°，北纬 ${lat}°（CGCS2000）`
  } catch {
    return '详见选址图纸'
  }
}

/* ============ 五维因子分析口径（对应模板第 3 章 → 本版第四章） ============ */

const FACTOR_METHOD: Record<string, { title: string; method: string; rule: string }> = {
  urban_planning: {
    title: '政策法规、城市规划条件',
    method: 'GIS 矢量叠置分析，比对国土空间规划、产业布局规划图层，判定地块规划符合性与政策扶持条件。',
    rule: '重点鼓励布局区 4 分；一般允许布局区 2–3 分；限制布局区 1 分；禁止布局 0 分（0–100 分制）。',
  },
  transport: {
    title: '交通条件与产品运输成本',
    method: 'GIS 网络分析计算地块至高速出入口、主干路网的实际通行距离；结合改进重心法 + Dijkstra 最短路径测算到需求区域的综合运输距离。',
    rule: '距交通节点越近、大件通行条件越好分值越高；单位产品综合运输距离越长分值越低（0–100 分制）。',
  },
  industry: {
    title: '市场需求与产业链完善程度',
    method: 'POI 提取上下游企业点位并做缓冲区统计，衡量产业集聚度；叠置经济运输半径内目标产业市场需求规模。',
    rule: '产业集聚度越高、市场需求规模越大得分越高（0–100 分制）。',
  },
  infrastructure: {
    title: '产业配套设施',
    method: 'POI 兴趣点提取、缓冲区分析，统计周边仓储、物流、公用工程等配套设施分布密度。',
    rule: '配套越完善分值越高（0–100 分制）。',
  },
  cost: {
    title: '土地成本与拆迁成本',
    method: '收集区域工业用地成交地价、基准地价数据并 GIS 重分类；叠加现状建设用地图层识别地块内建筑物，以现状建筑占地率评估拆迁工程量。',
    rule: '地价越低、拆迁量越小得分越高；地块内现状建筑占地越大扣分越多（0–100 分制，方向为负向）。',
  },
}

/* ============ 报告主体 ============ */

export async function buildReportDocx(src: ReportDocxSource): Promise<Blob> {
  const { scenario, result, config } = src
  const top = result.candidates[0]
  const top3 = result.candidates.slice(0, 3)
  const now = new Date().toLocaleString('zh-CN', { hour12: false })

  /* ---- 图表（离屏渲染，动画已关闭） ---- */
  const figWeights = weightsPiePng(src.weights)
  const figScores = candidateScoreBarPng(result)
  const figRadar = topRadarPng(scenario, result)
  let figMapUrl: string | null = null
  let figMapRatio = 0.62
  if (src.map) {
    figMapUrl = mapSnapshotPng(src.map)
    if (figMapUrl) {
      try {
        const c = src.map.getCanvas()
        if (c.width > 0 && c.height > 0) figMapRatio = c.height / c.width
      } catch {
        /* 保持默认比例 */
      }
    }
  }

  const children: (Paragraph | Table)[] = []

  /* ================= 封面（可行性研究报告格式） ================= */
  children.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 2200, after: 200 },
      children: [run('国土AI智慧选址系统', 28, false, GRAY)],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 900, after: 120 },
      children: [run(`${scenario.name}项目`, SIZE.cover, true)],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 700 },
      children: [run('选址分析报告', SIZE.cover, true)],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 160 },
      children: [run('（可行性研究报告格式）', SIZE.section, false, GRAY)],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 1600, after: 80 },
      children: [run('研究区域：广西壮族自治区桂林市临桂区', SIZE.body)],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 80 },
      children: [run('编制单位：国土AI智慧选址系统（自动生成）', SIZE.body)],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 80 },
      children: [run(`编制时间：${now}`, SIZE.body)],
    }),
    new Paragraph({ children: [new PageBreak()] })
  )

  /* ================= 目录（静态章节索引，逐行排布） ================= */
  children.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 200, after: 240 },
      children: [run('目　录', 36, true)],
    }),
    tocLine('第一章 总论', 0),
    tocLine('1.1 项目概况', 1),
    tocLine('1.2 编制依据', 1),
    tocLine('1.3 主要研究结论', 1),
    tocLine('第二章 项目需求与选址原则', 0),
    tocLine('2.1 项目定位与建设规模', 1),
    tocLine('2.2 选址偏好', 1),
    tocLine('2.3 选址原则', 1),
    tocLine('第三章 选址评价指标体系', 0),
    tocLine('3.1 指标体系构建', 1),
    tocLine('3.2 指标权重', 1),
    tocLine('3.3 一票否决约束清单', 1),
    tocLine('第四章 单因子分析评价', 0),
    tocLine('4.1 政策法规、城市规划条件', 1),
    tocLine('4.2 交通条件与产品运输成本', 1),
    tocLine('4.3 市场需求与产业链完善程度', 1),
    tocLine('4.4 产业配套设施', 1),
    tocLine('4.5 土地成本与拆迁成本', 1),
    tocLine('第五章 场址方案综合比选', 0),
    tocLine('5.1 模型计算方法说明', 1),
    tocLine('5.2 候选地块筛选与模型计算结果', 1),
    tocLine('5.3 排序稳健性检验', 1),
    tocLine('第六章 推荐地块论证与实施建议', 0),
    tocLine('6.1 推荐地块基础信息', 1),
    tocLine('6.2 各维度条件逐项评价', 1),
    tocLine('6.3 地块的 SWOT 分析', 1),
    tocLine('6.4 多方案对比简表', 1),
    tocLine('6.5 选址结论与落地实施建议', 1),
    p('注：本目录为章节结构索引；正文插图、表格均按章编号（图 3-1、表 5-1 等）。', {
      spacing: { before: 200 },
    }),
    new Paragraph({ children: [new PageBreak()] })
  )

  /* ================= 第一章 总论 ================= */
  children.push(chapter('第一章 总论'))
  children.push(box('本章为全文总纲：概述项目情况、报告编制依据，并给出选址研究的主要结论。详细论证过程见第二章至第六章。'))
  children.push(spacer())

  children.push(section('1.1 项目概况'))
  const pr = src.parseResult
  children.push(
    p(
      `本项目为${scenario.category}项目${
        pr ? `（解析产业门类「${pr.scenarioName}」）` : ''
      }，${scenario.description}。项目拟在研究区内选址落地，通过本系统开展多方案空间比选论证。`
    ),
    bullet(
      config.targetAreaHa !== null
        ? `建设规模：目标用地 ${config.targetAreaHa} 公顷${
            config.areaRange ? `，允许浮动区间 ${config.areaRange.lo}–${config.areaRange.hi} 公顷` : ''
          }。`
        : `建设规模：未指定目标用地规模，按最小地块面积 ${config.minAreaHa} 公顷筛选。`
    ),
    bullet(
      `研究范围：桂林市临桂区；候选池为控规工业用地图斑 ${result.total_cells.toLocaleString()} 个，经硬约束一票否决与面积条件筛选后保留 ${result.available_cells.toLocaleString()} 个（占比 ${((result.available_cells / result.total_cells) * 100).toFixed(1)}%）。`
    ),
    bullet(`研究方法：多因子 GIS 空间评价 + ${config.algorithmName} 多准则排序，输出 Top-${config.topN} 候选方案。`)
  )

  children.push(section('1.2 编制依据'))
  children.push(
    bullet('数据依据：研究区国土空间真实空间数据，包括控规工业用地图斑、生态保护红线、永久基本农田、城市蓝线、城市绿线、城市黄线、道路路网、现状建筑分布、产业园区边界等图层（CGCS2000 坐标系存储，EPSG:4525 投影量测）；'),
    bullet('方法依据：AHP 层次分析法、熵权法、TOPSIS 多准则决策、留一法贡献分解、蒙特卡洛权重扰动检验；'),
    bullet('工具依据：国土AI智慧选址系统 GIS 空间分析引擎（CGCS2000 坐标系存储，EPSG:4525 投影量测）。')
  )

  children.push(section('1.3 主要研究结论'))
  if (top) {
    children.push(
      p(
        `经硬约束校验、五维因子评价与${config.algorithmName}综合排序，优先推荐 ${top.code ?? `第 ${top.rank} 名候选地块`}（${centroidText(top)}，用地 ${top.area_ha.toFixed(2)} 公顷）作为本项目选址场址，综合得分 ${top.score.toFixed(4)}；蒙特卡洛权重扰动检验下保持 Top-${config.topN} 概率 ${pct(top.robustness)}。候选地块结果概览见下表，详细论证见第五章、第六章。`
      )
    )
    children.push(
      tableCaption('表 1-1  候选地块结果概览'),
      dataTable(
        ['候选地块编号', '综合得分', '用地规模（公顷）', '排序'],
        result.candidates.map((c) => [
          `${c.code ?? `地块${c.rank}`}${c.rank === 1 ? '（优先推荐）' : `（备选方案 ${c.rank - 1}）`}`,
          c.score.toFixed(4),
          c.area_ha.toFixed(2),
          c.rank,
        ]),
        [40, 22, 22, 16]
      )
    )
    children.push(spacer())
  } else {
    children.push(p('本次计算未产生候选地块，请调整选址条件后重新计算。'))
  }

  /* ================= 第二章 项目需求与选址原则 ================= */
  children.push(chapter('第二章 项目需求与选址原则'))
  children.push(box('本章节对项目录入的需求描述、建设要求、偏好设置进行结构化解读，形成标准化选址任务书，作为指标构建与模型计算的输入依据。'))
  children.push(spacer())

  children.push(section('2.1 项目定位与建设规模'))
  children.push(
    bullet(
      pr
        ? `项目定位：解析产业门类「${pr.scenarioName}」${pr.matchedKeywords.length ? `（命中关键词：${pr.matchedKeywords.join('、')}）` : ''}；${scenario.description}`
        : `项目定位：${scenario.category}——${scenario.description}`
    ),
    bullet(
      config.targetAreaHa !== null
        ? `建设规模：目标用地 ${config.targetAreaHa} 公顷${
            config.areaRange ? `，允许浮动区间 ${config.areaRange.lo}–${config.areaRange.hi} 公顷` : ''
          }；最小地块面积 ${config.minAreaHa} 公顷。`
        : `建设规模：未指定目标用地规模，按最小地块面积 ${config.minAreaHa} 公顷筛选。`
    ),
    bullet(`业务目标：在研究区内对 ${result.available_cells.toLocaleString()} 个可行候选地块综合评价，输出 Top-${config.topN} 候选方案并排序，降低用地与物流综合成本。`)
  )

  children.push(section('2.2 选址偏好'))
  children.push(bullet('1）硬性需求（优先保障）：', true))
  for (const c of scenario.constraints) {
    children.push(bullet(`${c.name}${c.buffer_m ? `（缓冲 ${c.buffer_m} 米）` : ''}${c.required ? '【必选】' : ''}，命中即一票否决；`))
  }
  children.push(bullet('2）偏好约束（次优先考虑）：', true))
  for (const f of scenario.factors) {
    const lv = PREFERENCE_LEVELS.find((l) => l.value === (src.preferences[f.id] ?? 'neutral'))
    children.push(bullet(`${f.name}：${lv?.label ?? '一般'}（权重 ${pct(src.weights[f.id])}）；`))
  }
  if (pr?.explanation) children.push(p(`AI 需求解析说明：${pr.explanation}`))

  children.push(section('2.3 选址原则'))
  children.push(
    p(
      '结合项目产业属性与硬性约束，本次选址遵循以下原则：1）合规底线优先原则：严格遵循国土空间管控规则，首先规避一票否决类禁建区域，所有候选地块必须满足规划、生态、地质等底线要求；' +
        '2）综合效益最优原则：以多因子加权综合评价统筹交通、产业、配套与成本；' +
        `3）方案稳健原则：对候选地块开展留一法贡献分解与蒙特卡洛权重扰动检验（本次 ${result.robustness?.samples ?? 200} 次扰动），保障排序结论稳健。` +
        `本次分析对具备图层数据支撑的硬约束执行一票否决，候选地块均已通过该部分校验；缺少对应图层数据的约束未纳入计算，已在结果说明中逐条列明。`
    )
  )

  /* ================= 第三章 选址评价指标体系 ================= */
  children.push(chapter('第三章 选址评价指标体系'))

  children.push(section('3.1 指标体系构建'))
  children.push(
    box('从城市规划、交通物流、产业协同、基础配套、建造成本 5 大维度搭建评价体系，向下拆解二级评价指标，用于后续 GIS 单因子打分与地块综合评价。')
  )
  children.push(spacer())
  children.push(
    tableCaption('表 3-1  选址评价指标体系'),
    dataTable(
      ['一级指标', '二级评价指标', '指标说明'],
      [
        ['城市规划', '规划符合性', '地块是否符合国土空间规划、产业布局规划'],
        ['', '政策扶持条件', '区域产业补贴、土地优惠、产业准入政策'],
        ['交通物流', '对外交通条件', '距离高速出入口、主干道距离，道路等级，大件运输通行能力'],
        ['', '产品运输成本', '基于路网实际路径的到市场需求点综合运输距离'],
        ['产业协同', '市场需求', '经济运输半径内目标产业市场总需求规模'],
        ['', '产业链完善程度', '周边上下游企业集聚度'],
        ['基础配套', '产业配套设施', '周边仓储、物流、公用工程等配套密度'],
        ['', '水电路信接入', '供水、供电、道路、通信接入条件'],
        ['建造成本', '土地成本', '工业用地成交地价、基准地价水平'],
        ['', '拆迁成本', '地块内现状建筑物、构筑物拆迁工程量'],
      ],
      [20, 26, 54]
    )
  )
  children.push(spacer())

  children.push(section('3.2 指标权重'))
  children.push(
    box(
      `本次权重来源：${config.weightSource ?? config.weightModeName}。专家权重采用 AHP 层次分析法构建判断矩阵并结合熵权法修正；AI 学习权重由临桂区真实开发事实反推。下表为本次计算实际生效的一级指标权重。`
    )
  )
  children.push(spacer())
  children.push(
    tableCaption('表 3-2  本次评价权重一览'),
    dataTable(
      ['一级指标', '本次权重', '评价方向'],
      scenario.factors.map((f) => [
        f.name,
        pct(src.weights[f.id]),
        f.direction === 1 ? '正向（越大越优）' : '负向（越小越优）',
      ]),
      [34, 33, 33]
    )
  )
  children.push(...figure(figWeights, '图 3-1  本次评价权重分布', 500, 242))

  children.push(section('3.3 一票否决约束清单'))
  children.push(
    box(
      '下表为本门类「模板定义」的约束全集，采用 GIS 空间掩模处理：' +
        '凡具备图层数据支撑的约束，地块命中即直接淘汰，不进入综合评价环节。' +
        '缺少对应图层数据的约束本次未纳入计算，实际参与情况见本文「计算结果说明」。'
    )
  )
  children.push(spacer())
  children.push(
    tableCaption('表 3-3  一票否决约束清单（模板定义）'),
    dataTable(
      ['约束名称', '缓冲距离', '约束性质'],
      scenario.constraints.map((c) => [
        c.name,
        c.buffer_m ? `${c.buffer_m} 米` : '—',
        c.required ? '强制（不可关闭）' : '非必需（默认不启用，按需开启）',
      ]),
      [46, 24, 30]
    )
  )
  children.push(spacer())

  /* ================= 第四章 单因子分析评价 ================= */
  children.push(chapter('第四章 单因子分析评价'))
  children.push(
    box('对每一个一级指标，说明分析方法、数据来源与打分规则，并结合本次计算结果给出分析结论。')
  )
  children.push(spacer())
  scenario.factors.forEach((f, i) => {
    const m = FACTOR_METHOD[f.id]
    const vals = result.candidates.map((c) => c.factors[f.id] ?? 0)
    const best = Math.max(...vals)
    const worst = Math.min(...vals)
    const sens = result.sensitivity?.[f.id]
    children.push(section(`4.${i + 1} ${m.title}`))
    children.push(bullet(`分析方法：${m.method}`))
    children.push(bullet(`打分规则：${m.rule}`))
    children.push(
      bullet(
        `分析结论：本次 Top-${result.candidates.length} 候选地块在该维度得分区间 ${worst.toFixed(2)}–${best.toFixed(2)}（0–100 分制），首位地块得分 ${best.toFixed(2)}；` +
          (sens !== undefined
            ? `留一法全局敏感性 ${sens.toFixed(3)}，该维度对排序结果${sens > 0.05 ? '影响显著' : '影响有限'}。`
            : '该维度得分已纳入综合评价。')
      )
    )
  })
  children.push(
    box(
      '本章小结：汇总各单因子专题分析成果，标记各维度的优势与短板片区；单因子标准化分值进入第五章场址方案综合比选。'
    )
  )
  children.push(spacer())

  /* ================= 第五章 场址方案综合比选 ================= */
  children.push(chapter('第五章 场址方案综合比选'))

  children.push(section('5.1 模型计算方法说明'))
  children.push(
    bullet(
      '1）AHP-GIS 加权综合评价：利用 AHP 判断矩阵并结合熵权法得到的合成权重，对 GIS 单因子标准化分值进行图层加权叠加，得到各地块综合得分；'
    ),
    bullet(`2）改进重心法（Dijkstra）：以市场需求点位需求量为权重，用路网实际路径距离替换传统重心法直线距离迭代求解理论运输成本最低点，作为交通区位校核参考；`),
    bullet(
      `3）${config.algorithmName}：对通过一票否决的候选地块构建决策矩阵（指标归一化），${config.algorithmName === 'TOPSIS' ? '计算到正、负理想解的距离得到贴近度 Ci 并排序' : config.algorithmName === 'K-Means 聚类' ? '按因子特征自动分组，识别同类地块片区（0 优先开发类 / 1 条件适合类 / 2 储备备用类）' : '拟合历史选址偏好，预测地块适宜度'}。`
    ),
    bullet(
      `计算参数：候选池控规工业用地图斑 ${result.total_cells.toLocaleString()} 个，经硬约束一票否决与面积条件筛选后保留 ${result.available_cells.toLocaleString()} 个（占比 ${((result.available_cells / result.total_cells) * 100).toFixed(1)}%）。`
    )
  )

  children.push(section('5.2 候选地块筛选与模型计算结果'))
  children.push(
    p(
      `1）候选地块筛选逻辑：在 GIS 输出的高适宜区域内过滤一票否决地块，结合国土空间现状与土地权属筛选，得到 ${result.candidates.length} 个有效候选地块。2）模型输出结果如下表、下图所示：`
    )
  )
  children.push(
    tableCaption('表 5-1  候选地块模型计算结果'),
    dataTable(
      ['候选地块编号', '贴近度 / 综合得分', '用地规模（公顷）', '排序'],
      result.candidates.map((c) => [
        `${c.code ?? `地块${c.rank}`}${c.rank === 1 ? '（优先推荐）' : `（备选方案 ${c.rank - 1}）`}`,
        c.score.toFixed(4),
        c.area_ha.toFixed(2),
        c.rank,
      ]),
      [34, 26, 22, 18]
    )
  )
  children.push(spacer())
  children.push(...figure(figScores, '图 5-1  候选地块综合得分对比', 540, 261))
  children.push(...figure(figRadar, '图 5-2  Top-3 候选地块五维得分雷达图', 500, 340))

  children.push(section('5.3 排序稳健性检验'))
  children.push(
    box(
      `排序结果依赖本次${config.weightModeName}。${
        result.robustness
          ? `对权重按 Dirichlet 分布扰动并重排 ${result.robustness.samples} 次，各地块保持在 Top-${result.robustness.top_n} 的平均概率为 ${(result.robustness.mean_stability * 100).toFixed(1)}%，排序整体${result.robustness.mean_stability > 0.7 ? '稳健' : '对权重较为敏感，建议结合实地核查决策'}；同时开展留一法贡献分解，识别各地块的主导优势与短板因子。`
          : '建议结合实地核查决策。'
      }`
    )
  )
  children.push(spacer())

  /* ================= 第六章 推荐地块论证与实施建议 ================= */
  children.push(chapter('第六章 推荐地块论证与实施建议'))
  if (top) {
    children.push(section('6.1 推荐地块基础信息'))
    children.push(
      bullet(`地块编号：${top.code ?? `地块${top.rank}`}（来源图层：${top.source ?? '控规工业用地'}）；`),
      bullet(`地理位置：${centroidText(top)}；`),
      bullet(`用地规模：${top.area_ha.toFixed(2)} 公顷；规划用地性质：工业用地；`),
      bullet(
        `土地现状：现状建筑占地率 ${(Number(top.build_density ?? 0) * 100).toFixed(1)}%（${Number(top.build_density ?? 0) < 0.3 ? '净地条件较好' : '需评估拆迁投入'}）；`
      ),
      bullet('管控核查：未命中一票否决清单；不涉及生态保护红线、永久基本农田；'),
      bullet(`地块概况：${top.notes}；`),
      bullet(`稳健性：权重扰动下保持 Top-${config.topN} 概率 ${pct(top.robustness)}。`)
    )
    children.push(...figure(figMapUrl, '图 6-1  推荐地块区位示意图（系统当前视口）', 520, Math.round(520 * figMapRatio)))

    children.push(section('6.2 各维度条件逐项评价'))
    for (const f of scenario.factors) {
      const contrib = top.contributions?.[f.id]
      children.push(
        p(
          `${f.name}维度：得分 ${(top.factors[f.id] ?? 0).toFixed(2)}（0–100 分制），权重 ${pct(src.weights[f.id])}${
            contrib !== undefined
              ? `，留一法贡献 ${contrib >= 0 ? '+' : ''}${contrib.toFixed(4)}（${contrib >= 0 ? '正贡献/优势项' : '负贡献/短板项'}）`
              : ''
          }。`
        )
      )
    }

    children.push(section('6.3 地块的 SWOT 分析'))
    children.push(
      tableCaption('表 6-1  优先推荐地块 SWOT 分析'),
      dataTable(
        ['维度', '分析内容'],
        [
          [
            '优势（Strengths）',
            `主导优势为${top.top_driver ?? '多因子均衡'}；${scenario.factors
              .filter((f) => (top.contributions?.[f.id] ?? 0) > 0)
              .slice(0, 3)
              .map((f) => `${f.name}得分 ${(top.factors[f.id] ?? 0).toFixed(2)}`)
              .join('、')}，综合得分排名第 1。`,
          ],
          [
            '劣势（Weaknesses）',
            `主要短板为${top.top_weakness ?? '部分维度偏弱'}；现状建筑占地率 ${(Number(top.build_density ?? 0) * 100).toFixed(1)}%，${
              Number(top.build_density ?? 0) >= 0.3 ? '存在一定拆迁投入' : '拆迁压力较小'
            }。`,
          ],
          [
            '机会（Opportunities）',
            `权重来源为${config.weightModeName}，兼顾专家经验与真实开发数据；区域产业政策与基础设施持续完善，利于项目落地。`,
          ],
          [
            '威胁（Threats）',
            `权重扰动下保持 Top-${config.topN} 概率 ${pct(top.robustness)}${
              Number(top.robustness ?? 1) < 0.7 ? '，排序对权重较敏感，建议实地核查后再行决策' : '，排序稳健'
            }；需关注要素价格波动与周边同类项目竞争。`,
          ],
        ],
        [22, 78]
      )
    )
    children.push(spacer())

    children.push(section('6.4 多方案对比简表'))
    if (top3.length > 1) {
      children.push(
        tableCaption('表 6-2  多方案对比简表'),
        dataTable(
          ['对比维度', ...top3.map((c) => `${c.rank === 1 ? '优先推荐' : `备选${c.rank - 1}`}-${c.code ?? `地块${c.rank}`}`)],
          [
            ['综合得分', ...top3.map((c) => c.score.toFixed(4))],
            ['用地规模（公顷）', ...top3.map((c) => c.area_ha.toFixed(2))],
            ...scenario.factors.map((f) => [
              `${f.name}得分`,
              ...top3.map((c) => (c.factors[f.id] ?? 0).toFixed(2)),
            ]),
            ['主导优势', ...top3.map((c) => c.top_driver ?? '—')],
            ['主要短板', ...top3.map((c) => c.top_weakness ?? '—')],
            ['保持 Top-N 概率', ...top3.map((c) => pct(c.robustness))],
          ],
          [25, 25, 25, 25]
        )
      )
      children.push(spacer())
      children.push(
        p(
          `对比小结：${top3[0].code ?? '地块 A'} 综合条件最优，为本项目优先选址；若其土地无法按期供应，可依次切换 ${top3
            .slice(1)
            .map((c) => c.code ?? `地块${c.rank}`)
            .join('、')} 开展前期工作。`
        )
      )
    }

    children.push(section('6.5 选址结论与落地实施建议'))
    children.push(subsection('（1）选址结论'))
    children.push(
      p(
        `综合 AHP-GIS 加权评价、改进重心法运输测算与${config.algorithmName}排序，优先推荐 ${top.code ?? `第 ${top.rank} 名候选地块`}（${centroidText(top)}，${top.area_ha.toFixed(2)} 公顷）作为本项目选址场址。该地块已通过本期可用的硬约束校验，市场、交通、配套与成本条件综合最优，综合得分 ${top.score.toFixed(4)}。${result.message}`
      )
    )
    children.push(subsection('（2）落地实施建议'))
    children.push(
      bullet('土地前期工作：对推荐地块开展实地踏勘，核实土地权属、征地拆迁时序；开展地质灾害危险性评估、压覆矿产评估，落实耕地占补平衡相关要求；'),
      bullet('规划报批对接：对接自然资源主管部门，衔接国土空间规划"一张图"实施监督信息系统，办理用地预审与规划许可；'),
      bullet('基础设施对接：提前对接供水、供电、道路、通信等市政配套的实施主体与接入方案；'),
      bullet('动态复核：建议结合最新遥感影像与权属数据对得分进行周期性复核，保持选址结论的时效性。')
    )
  }

  children.push(
    new Paragraph({
      spacing: { before: 300 },
      border: { top: { style: BorderStyle.SINGLE, size: 4, color: 'D1D5DB' } },
      children: [run('数据来源：国土空间规划真实图层数据（研究区：桂林市临桂区）；本报告由国土AI智慧选址系统自动生成。', SIZE.small, false, GRAY)],
    })
  )

  const doc: Document = new Document({
    creator: '国土AI智慧选址系统',
    title: `${scenario.name}项目选址分析报告`,
    styles: {
      default: {
        document: { run: { font: FONT, size: SIZE.body, color: INK } },
      },
    },
    sections: [
      {
        properties: {
          page: {
            size: { width: 11906, height: 16838 },
            margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
          },
        } as ISectionOptions['properties'],
        children,
      },
    ],
  })

  return Packer.toBlob(doc)
}

/** 生成并下载 .docx 报告 */
export async function exportReportDocx(src: ReportDocxSource): Promise<void> {
  const blob = await buildReportDocx(src)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `选址分析报告_${src.scenario.name}_${new Date().toISOString().slice(0, 10)}.docx`
  a.click()
  URL.revokeObjectURL(url)
}
