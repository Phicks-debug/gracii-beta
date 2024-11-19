export type FileType = 'document' | 'data' | 'image';

export interface FileUpload {
  id: string;
  file: File;
  type: FileType;
  preview?: string;
}

export const ACCEPTED_FILE_TYPES = {
  document: '.doc,.docx,.pdf,.txt',
  data: '.xlsx,.csv,.json',
  image: 'image/*'
} as const;

export const FILE_TYPE_ICONS = {
  document: '📄',
  data: '📊',
  image: '🖼️'
} as const;

export const FILE_TYPE_LABELS = {
  document: 'Document',
  data: 'Data File',
  image: 'Image'
} as const;
