import React, { useEffect, useState } from 'react';
import { X, FileIcon, FileText, Database } from 'lucide-react';
import { FileUpload } from './types';

interface FilePreviewProps {
  upload: FileUpload;
  onRemove: (id: string) => void;
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
};

const getFileIcon = (type: string) => {
  switch (type) {
    case 'document':
      return <FileText className="w-8 h-8 text-blue-400" />;
    case 'data':
      return <Database className="w-8 h-8 text-purple-400" />;
    default:
      return <FileIcon className="w-8 h-8 text-gray-400" />;
  }
};

export const FilePreview: React.FC<FilePreviewProps> = ({ upload, onRemove }) => {
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<boolean>(false);

  useEffect(() => {
    const generatePreview = async () => {
      try {
        if (upload.file.type.startsWith('image/')) {
          // Image preview
          setPreview(URL.createObjectURL(upload.file));
        } else if (
          upload.file.type === 'text/plain' ||
          upload.file.type === 'application/json' ||
          upload.file.name.endsWith('.txt') ||
          upload.file.name.endsWith('.json')
        ) {
          // Text file preview
          const text = await upload.file.text();
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d');
          if (ctx) {
            canvas.width = 100;
            canvas.height = 80;
            ctx.fillStyle = '#f3f4f6';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.font = '10px monospace';
            ctx.fillStyle = '#374151';
            
            const lines = text.split('\\n').slice(0, 6);
            lines.forEach((line, i) => {
              ctx.fillText(line.slice(0, 15), 5, 15 + (i * 12));
            });
            
            setPreview(canvas.toDataURL());
          }
        } else if (upload.file.type === 'application/pdf') {
          // For PDFs, we'll show the first page when possible
          // Note: This requires pdf.js for full implementation
          setPreview(null);
        } else if (
          upload.file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
          upload.file.type === 'application/vnd.ms-excel' ||
          upload.file.name.endsWith('.xlsx') ||
          upload.file.name.endsWith('.xls')
        ) {
          // For Excel files, show a grid preview
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d');
          if (ctx) {
            canvas.width = 100;
            canvas.height = 80;
            ctx.fillStyle = '#f3f4f6';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            // Draw grid lines
            ctx.strokeStyle = '#d1d5db';
            ctx.lineWidth = 0.5;
            for (let i = 0; i < 6; i++) {
              // Horizontal lines
              ctx.beginPath();
              ctx.moveTo(0, i * 15);
              ctx.lineTo(100, i * 15);
              ctx.stroke();
              // Vertical lines
              ctx.beginPath();
              ctx.moveTo(i * 20, 0);
              ctx.lineTo(i * 20, 80);
              ctx.stroke();
            }
            
            setPreview(canvas.toDataURL());
          }
        }
      } catch (err) {
        console.error('Error generating preview:', err);
        setError(true);
      }
    };

    generatePreview();
    return () => {
      if (preview) URL.revokeObjectURL(preview);
    };
  }, [upload.file]);

  return (
    <div className="inline-block relative w-[100px] h-[80px] m-1 group">
      <div className="w-full h-full bg-gray-100 rounded-lg border border-gray-200 overflow-hidden">
        {preview ? (
          <img 
            src={preview} 
            alt="" 
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gray-50">
            {error ? (
              <div className="text-red-500 text-xs text-center px-1">
                Preview unavailable
              </div>
            ) : (
              getFileIcon(upload.type)
            )}
          </div>
        )}
        
        {/* Overlay with file info */}
        <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-50 transition-all duration-200 flex flex-col justify-end p-1.5">
          <div className="text-white transform translate-y-full group-hover:translate-y-0 transition-transform duration-200">
            <p className="text-xs truncate">{upload.file.name}</p>
            <p className="text-[10px] opacity-75">{formatFileSize(upload.file.size)}</p>
          </div>
        </div>

        {/* Remove button */}
        <button
          onClick={() => onRemove(upload.id)}
          className="absolute top-0.5 right-0.5 p-0.5 rounded-full bg-white opacity-0 group-hover:opacity-100 transition-opacity duration-200 hover:bg-gray-100"
          aria-label="Remove file"
        >
          <X className="w-3.5 h-3.5 text-gray-600" />
        </button>
      </div>
    </div>
  );
};
