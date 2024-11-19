import React from 'react';
import { motion } from 'framer-motion';
import { FileText, Database, Image } from 'lucide-react';
import { FileType, FILE_TYPE_LABELS } from './types';

interface UploadMenuProps {
  onSelectType: (type: FileType) => void;
}

const UPLOAD_OPTIONS = [
  { type: 'document' as FileType, icon: FileText, color: 'text-blue-500', label: FILE_TYPE_LABELS.document },
  { type: 'data' as FileType, icon: Database, color: 'text-purple-500', label: FILE_TYPE_LABELS.data },
  { type: 'image' as FileType, icon: Image, color: 'text-green-500', label: FILE_TYPE_LABELS.image }
];

export const UploadMenu: React.FC<UploadMenuProps> = ({ onSelectType }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      className="absolute bottom-full left-0 mb-2 bg-white rounded-lg shadow-lg p-2 w-48 z-50"
    >
      {UPLOAD_OPTIONS.map(({ type, icon: Icon, color, label }) => (
        <button
          key={type}
          onClick={() => onSelectType(type)}
          className="flex items-center w-full p-2 hover:bg-gray-100 rounded transition-colors duration-200"
        >
          <Icon className={`w-5 h-5 mr-2 ${color}`} />
          <span className="text-sm text-gray-700">{label}</span>
        </button>
      ))}
    </motion.div>
  );
};
