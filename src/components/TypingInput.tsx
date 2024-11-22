import React, { useState, useRef, useEffect } from 'react';

interface TypingInputProps {
    value: string;
    onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
    onKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
    placeholder: string;
    disabled: boolean;
}

export const TypingInput = ({
    value,
    onChange,
    onKeyDown,
    placeholder,
    disabled,
}: TypingInputProps) => {
    const [cursorPosition, setCursorPosition] = useState(0);
    const [, setIsActive] = useState(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const cursorRef = useRef<HTMLDivElement>(null);
    const timeoutRef = useRef<number>();

    const resetTimer = () => {
        if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
        }
        setIsActive(true);
        timeoutRef.current = setTimeout(() => {
            setIsActive(false);
        }, 2000);
    };

    const adjustHeight = () => {
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = "auto";
            const newHeight = Math.min(textarea.scrollHeight, 208);
            textarea.style.height = `${newHeight}px`;
            textarea.style.overflowY = textarea.scrollHeight > 208 ? 'auto' : 'hidden';
        }
    };

    useEffect(() => {
        return () => {
            if (timeoutRef.current) {
                clearTimeout(timeoutRef.current);
            }
        };
    }, []);

    // const handleSelectionChange = (
    //     e: React.SyntheticEvent<HTMLTextAreaElement>
    // ) => {
    //     const target = e.target as HTMLTextAreaElement;
    //     setCursorPosition(target.selectionStart || 0);
    // };

    const updateCursorPosition = () => {
        if (textareaRef.current && cursorRef.current) {
            const textarea = textareaRef.current;
            const cursorPos = textarea.selectionStart || 0;

            const styles = window.getComputedStyle(textarea);
            const paddingLeft = parseInt(styles.paddingLeft);

            const span = document.createElement("span");
            span.style.cssText = `
        font: ${styles.font};
        letter-spacing: ${styles.letterSpacing};
        position: absolute;
        visibility: hidden;
        white-space: pre;
      `;

            const textBeforeCursor = value
                .substring(0, cursorPos)
                .replace(/ /g, "\u00A0");

            span.textContent = textBeforeCursor;
            document.body.appendChild(span);

            const cursorX = span.offsetWidth + paddingLeft;
            document.body.removeChild(span);

            cursorRef.current.style.transform = `translateX(${cursorX}px)`;
            setCursorPosition(cursorPos);
            resetTimer();
        }
    };

    const handleInteraction = () => {
        resetTimer();
    };

    useEffect(() => {
        updateCursorPosition();
    }, [value, cursorPosition]);

    return (
        <div className="typing-input-container relative max-h-52 overflow-hidden">
            <textarea
                ref={textareaRef}
                value={value}
                onChange={(e) => {
                    onChange(e);
                    handleInteraction();
                }}
                onKeyDown={(e) => {
                    onKeyDown(e);
                    handleInteraction();
                }}
                onSelect={(_e) => {
                    updateCursorPosition();
                    handleInteraction();
                }}
                onClick={(_e) => {
                    updateCursorPosition();
                    handleInteraction();
                }}
                onInput={adjustHeight}
                onMouseMove={handleInteraction}
                placeholder={placeholder}
                disabled={disabled}
                className="w-full px-4 pt-3 bg-transparent text-gray-800 focus:outline-none resize-none max-h-52 overflow-y-auto min-h-10 antialiased transition-all"
                style={{
                    fontFamily: "'Inter', monospace",
                    fontSize: "16px",
                    overflowY: 'auto',
                    maxHeight: '208px',
                }}
                rows={1}
            />
        </div>
    );
};