import { format, parseISO } from 'date-fns';

export function formatDate(dateStr: string | null | undefined, fmt = 'yyyy-MM-dd'): string {
  if (!dateStr) return '-';
  try {
    return format(parseISO(dateStr), fmt);
  } catch {
    return dateStr;
  }
}

export function formatDateTime(dateStr: string | null | undefined): string {
  return formatDate(dateStr, 'yyyy-MM-dd HH:mm:ss');
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

export function truncateId(id: string, len = 8): string {
  if (id.length <= len) return id;
  return id.substring(0, len) + '...';
}
