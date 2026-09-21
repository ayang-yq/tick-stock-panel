// @vitest-environment node
import { describe, expect, it } from 'vitest'
import { getSortValue } from './stock-table'
import type { ColumnConfig } from './list-columns'

function builtinCol(key: string): ColumnConfig {
  return { id: `builtin:${key}`, source: { type: 'builtin', key }, label: key, visible: false, align: 'center' }
}

describe('getSortValue: 自选加入信息列', () => {
  it('added_at 返回北京时间完整串 (与展示同口径, 字典序即时间序)', () => {
    expect(getSortValue({ added_at: '2026-09-18T20:30:00' }, builtinCol('added_at')))
      .toBe('2026-09-19 04:30:00')
  })

  it('added_at 缺失返回 null 而非空串', () => {
    // useTableSort 会先试 Number('') === 0, 返回空串会让空值排到最前
    for (const v of ['', null, undefined]) {
      expect(getSortValue({ added_at: v }, builtinCol('added_at'))).toBe(null)
    }
  })

  it('pct_since_added 透传数值 (含 0 与负值)', () => {
    expect(getSortValue({ pct_since_added: 0.1 }, builtinCol('pct_since_added'))).toBe(0.1)
    expect(getSortValue({ pct_since_added: -0.05 }, builtinCol('pct_since_added'))).toBe(-0.05)
    expect(getSortValue({ pct_since_added: 0 }, builtinCol('pct_since_added'))).toBe(0)
    expect(getSortValue({}, builtinCol('pct_since_added'))).toBe(undefined)
  })
})

describe('getSortValue: 新增内置列 (估值/财务/日历)', () => {
  it('估值列同名透传 (pe_ttm/pb/pe_forward)', () => {
    const r = { pe_ttm: 18.4, pb: 2.31, pe_forward: 12.7 }
    expect(getSortValue(r, builtinCol('pe_ttm'))).toBe(18.4)
    expect(getSortValue(r, builtinCol('pb'))).toBe(2.31)
    expect(getSortValue(r, builtinCol('pe_forward'))).toBe(12.7)
  })

  it('财务列同名透传 (roe/eps/净利率等)', () => {
    const r = { roe: 12.6, eps: 1.2, gross_margin: 55.3, net_margin: 21.0, revenue_yoy: 8.4, net_income_yoy: -3.2, debt_ratio: 44.1, bps: 9.9 }
    for (const k of ['roe', 'eps', 'gross_margin', 'net_margin', 'revenue_yoy', 'net_income_yoy', 'debt_ratio', 'bps']) {
      expect(getSortValue(r, builtinCol(k))).toBe((r as any)[k])
    }
  })

  it('缺值返回 null, 不返回 undefined/对象', () => {
    expect(getSortValue({}, builtinCol('pe_ttm'))).toBe(null)
    expect(getSortValue({ pe_ttm: null }, builtinCol('pe_ttm'))).toBe(null)
    // 对象/数组型字段不得当排序标量
    expect(getSortValue({ candles: [1, 2] }, builtinCol('candles'))).toBe(null)
    expect(getSortValue({ foo: { a: 1 } }, builtinCol('foo'))).toBe(null)
  })

  it('分位列与单元格同口径: 亏损股回落 PB 分位', () => {
    const loss = { pct_1y: null, pb_pct_1y: 0.42 }
    expect(getSortValue(loss, builtinCol('pct_1y'))).toBe(0.42)
    const profit = { pct_1y: 0.81, pb_pct_1y: 0.42 }
    expect(getSortValue(profit, builtinCol('pct_1y'))).toBe(0.81)
    // PB 系列不回落, 只看自己的窗口
    expect(getSortValue(profit, builtinCol('pb_pct_1y'))).toBe(0.42)
    expect(getSortValue({ pct_5y: 0.13 }, builtinCol('pct_5y'))).toBe(0.13)
    expect(getSortValue({}, builtinCol('pct_3y'))).toBe(null)
  })

  it('next_report 用日期串排序 (字典序=时间序), 缺失返回 null', () => {
    expect(getSortValue({ next_report_date: '2026-10-25' }, builtinCol('next_report'))).toBe('2026-10-25')
    expect(getSortValue({ next_report_period: '2026三季报' }, builtinCol('next_report'))).toBe(null)
  })
})
