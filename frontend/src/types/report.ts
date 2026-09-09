/** 报告生成与导出类型（模块 7） */

export type ExportFormat = 'pdf' | 'excel' | 'image'

export interface ReportSection {
  title: string
  content: string
}

export interface ReportDoc {
  title: string
  generatedAt: string
  scenarioName: string
  sections: ReportSection[]
  sampleData: true
}
