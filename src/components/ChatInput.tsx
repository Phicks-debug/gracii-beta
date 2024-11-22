import React from 'react';
import { ArrowUp, Paperclip } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { TypingInput } from './TypingInput';
import { FilePreview } from './FileUpload';
import { UploadMenu } from './FileUpload';
import { FileUpload } from './FileUpload';
import { ACCEPTED_FILE_TYPES } from './FileUpload';

interface ChatInputProps {
    input: string;
    setInput: (value: string) => void;
    handleSubmit: (e: React.FormEvent) => void;
    handleKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
    isStreaming: boolean;
    hasInteracted: boolean;
    uploads: FileUpload[];
    isUploadMenuOpen: boolean;
    setIsUploadMenuOpen: (value: boolean) => void;
    handleFileType: (type: any) => void;
    removeUpload: (id: string) => void;
    fileInputRef: React.RefObject<HTMLInputElement>;
    handleFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

const formVariants = {
    hidden: {
        opacity: 0,
        y: -50,
    },
    visible: {
        opacity: 1,
        y: 0,
        transition: {
            duration: 1,
            ease: "easeOut",
        },
    },
};

export const ChatInput: React.FC<ChatInputProps> = ({
    input,
    setInput,
    handleSubmit,
    handleKeyDown,
    isStreaming,
    hasInteracted,
    uploads,
    isUploadMenuOpen,
    setIsUploadMenuOpen,
    handleFileType,
    removeUpload,
    fileInputRef,
    handleFileChange,
}) => {
    return (
        <div
            className={`bg-gray-100 transition-all duration-300 ease-in-out ${hasInteracted ? "" : "mb-20.5%"
                } relative z-30`}
        >
            <motion.form
                onSubmit={handleSubmit}
                className={`mx-auto duration-300 ease-in-out ${hasInteracted ? "max-w-3xl" : "max-w-2xl"
                    }`}
                variants={formVariants}
            >
                <div className="relative flex flex-col bg-white rounded-3xl shadow-md">
                    {uploads.length > 0 && (
                        <div className="px-3 py-2 flex flex-wrap gap-1 border-b border-gray-100">
                            {uploads.map((upload) => (
                                <FilePreview
                                    key={upload.id}
                                    upload={upload}
                                    onRemove={removeUpload}
                                />
                            ))}
                        </div>
                    )}
                    <TypingInput
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Tell something to Gracii..."
                        disabled={isStreaming}
                    />
                    <div className="relative flex px-2">
                        <div className="relative self-end">
                            <button
                                type="button"
                                onClick={() => setIsUploadMenuOpen(!isUploadMenuOpen)}
                                className="shrink-0 p-1 text-gray-500 hover:text-gray-700 focus:outline-none self-end mb-2 ml-1"
                            >
                                <Paperclip className="w-6 h-6" />
                            </button>

                            <AnimatePresence>
                                {isUploadMenuOpen && (
                                    <UploadMenu onSelectType={handleFileType} />
                                )}
                            </AnimatePresence>
                        </div>

                        <input
                            type="file"
                            ref={fileInputRef}
                            onChange={handleFileChange}
                            className="hidden"
                            accept={Object.values(ACCEPTED_FILE_TYPES).join(",")}
                        />

                        <div className="flex-1 mb-0.5 min-h-[44px] flex flex-col justify-end"></div>

                        <div className="self-end">
                            <button
                                type="submit"
                                disabled={!input.trim() && uploads.length === 0}
                                className={`bg-[#000] text-white rounded-full shrink-0 ml-1 mb-2 p-1 focus:outline-none self-end transition-opacity duration-200 ${!input.trim() && uploads.length === 0
                                    ? "opacity-10 cursor-not-allowed"
                                    : "hover:opacity-70"
                                    }`}
                            >
                                <ArrowUp className="w-6 h-6" />
                            </button>
                        </div>
                    </div>
                </div>
            </motion.form>
            <div>
                <span className="flex justify-center text-gray-500 text-xs p-2">
                    A product from TechX Coporation's Research and Development Teams.
                </span>
            </div>
        </div>
    );
};