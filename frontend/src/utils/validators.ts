export function isValidCsvFile(file: File): boolean {
  return file.name.endsWith('.csv') || file.type === 'text/csv' || file.type === 'application/vnd.ms-excel';
}

export function isNonEmptyCsv(file: File): boolean {
  return file.size > 0;
}

export function validateUploadFile(file: File): string | null {
  if (!isValidCsvFile(file)) return 'Only CSV files are supported';
  if (!isNonEmptyCsv(file)) return 'File is empty';
  return null;
}
