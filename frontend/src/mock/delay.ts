/**
 * Mock 工具：延迟 + 进度推流。
 * 所有 mock 数据仅用于演示，UI 界面统一标注「样例数据 SAMPLE」。
 */

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export interface ProgressTick {
  percent: number
  log: string
  label: string
}

/**
 * 模拟分阶段计算进度（0 → 100%），每阶段回调一次。
 * @param onTick 进度回调
 * @param stages 自定义阶段（默认五阶段选址流程）
 */
export async function runWithProgress(
  onTick: (t: ProgressTick) => void,
  stages: { label: string; percent: number; ms: number }[] = DEFAULT_STAGES
): Promise<void> {
  for (const s of stages) {
    await sleep(s.ms)
    onTick({ percent: s.percent, log: `[${new Date().toLocaleTimeString()}] ${s.label}`, label: s.label })
  }
}

const DEFAULT_STAGES = [
  { label: '空间数据预处理中…', percent: 20, ms: 500 },
  { label: '初选 GIS 加权计算中…', percent: 45, ms: 600 },
  { label: '精选评价计算中…', percent: 70, ms: 600 },
  { label: '结果组装中…', percent: 90, ms: 500 },
  { label: '分析完成，详细结果见页面右侧面板', percent: 100, ms: 400 },
]
