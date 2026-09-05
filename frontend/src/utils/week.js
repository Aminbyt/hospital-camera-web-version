export function startOfWeek(base = new Date(), offsetWeeks = 0) {
  const d = new Date(base.getFullYear(), base.getMonth(), base.getDate())
  const day = d.getDay() || 7
  d.setDate(d.getDate() - day + 1 - offsetWeeks * 7)
  d.setHours(0,0,0,0)
  return d
}
export function endOfWeek(start) { const d=new Date(start); d.setDate(d.getDate()+6); d.setHours(23,59,59,999); return d }
export function ymd(d){ const y=d.getFullYear(),m=String(d.getMonth()+1).padStart(2,'0'),day=String(d.getDate()).padStart(2,'0'); return `${y}-${m}-${day}` }
export function weekRange(offset=0){const start=startOfWeek(new Date(),offset),end=endOfWeek(start);return {start,end,date_from:ymd(start),date_to:ymd(end)}}
export function weekLabel(offset=0){const {start,end}=weekRange(offset);const fmt=new Intl.DateTimeFormat(undefined,{month:'short',day:'numeric'});return `${fmt.format(start)} – ${fmt.format(end)}`}
