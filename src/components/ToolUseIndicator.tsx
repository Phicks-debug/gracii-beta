import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from "framer-motion";

interface ToolUseIndicatorProps {
    isDone?: boolean;
    isThinking?: boolean;
}

export const ToolUseIndicator = ({
    isDone,
    isThinking,
}: ToolUseIndicatorProps) => {
    const [dots, setDots] = useState("...");
    const [isExpanded, setIsExpanded] = useState(false);

    useEffect(() => {
        if (!isDone) {
            const interval = setInterval(() => {
                setDots((prev) => (prev.length >= 6 ? "." : prev + "."));
            }, 300);
            return () => clearInterval(interval);
        }
    }, [isDone]);

    return (
        <div className="relative">
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="group cursor-pointer"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <span
                    className={`text-sm ${isDone
                        ? "text-green-600 dark:text-green-400"
                        : "text-gray-500 dark:text-gray-400 animate-[pulse_0.8s_ease-in-out_infinite]"
                        }`}
                >
                    {isDone
                        ? "✓ Tools used"
                        : isThinking
                            ? `Thinking${dots}`
                            : `Using tools${dots}`}
                </span>

                <AnimatePresence>
                    {isExpanded && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            className="absolute left-0 top-6 z-10 bg-gray-100 dark:bg-gray-700 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-600 min-w-[200px]"
                        >
                            <div className="text-base text-gray-600 dark:text-gray-300">
                                {isDone ? (
                                    <>
                                        <div className="font-medium mb-1">
                                            Tools executed successfully
                                        </div>
                                        <div className="text-sm text-gray-500">
                                            All requested operations completed
                                        </div>
                                    </>
                                ) : isThinking ? (
                                    <>
                                        <div className="font-medium mb-1">Processing response</div>
                                        <div className="text-sm text-gray-500">
                                            Analyzing tool results
                                        </div>
                                    </>
                                ) : (
                                    <>
                                        <div className="font-medium mb-1">
                                            Processing with tools
                                        </div>
                                        <div className="text-sm text-gray-500">
                                            Executing operations and gathering results
                                        </div>
                                    </>
                                )}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.div>
        </div>
    );
};