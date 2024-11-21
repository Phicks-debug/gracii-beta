import React, { useState, useRef, useEffect, useCallback } from "react";
import { ArrowUp, Paperclip } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileUpload,
  UploadMenu,
  FilePreview,
  FileType,
  ACCEPTED_FILE_TYPES,
} from "./components/FileUpload";

interface Message {
  id: number;
  content: string;
  role: "user" | "bot";
  toolUse?: boolean;
  toolDone?: boolean;
  isThinking?: boolean;
}

const ToolUseIndicator = ({
  isDone,
  isThinking,
}: {
  isDone?: boolean;
  isThinking?: boolean;
}) => {
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

const TypingInput = ({
  value,
  onChange,
  onKeyDown,
  placeholder,
  disabled,
}: {
  value: string;
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  placeholder: string;
  disabled: boolean;
}) => {
  const [cursorPosition, setCursorPosition] = useState(0);
  const [isActive, setIsActive] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const cursorRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<NodeJS.Timeout>();

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
      textarea.style.height = "auto"; // Reset height to recalculate
      textarea.style.height = `${Math.min(textarea.scrollHeight, 208)}px`; // Limit to max height
    }
  };

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

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

      // Apply transform with transition
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
    <div className="typing-input-container relative">
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
        onSelect={(e) => {
          updateCursorPosition();
          handleInteraction();
        }}
        onClick={(e) => {
          updateCursorPosition();
          handleInteraction();
        }}
        onInput={adjustHeight}
        onMouseMove={handleInteraction}
        placeholder={placeholder}
        disabled={disabled}
        className="w-full px-4 pt-3 bg-transparent text-gray-800 focus:outline-none resize-none max-h-52 overflow-y-auto min-h-10"
        style={{
          fontFamily: "'Inter', monospace",
          fontSize: "16px",
        }}
        rows={1}
      />
      {/* <div
        ref={cursorRef}
        className={`typing-cursor ${isActive ? 'cursor-visible' : 'cursor-hidden'}`}
        style={{
          top: '12px',
          height: '18px'
        }}
      /> */}
    </div>
  );
};

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [showHeader, setShowHeader] = useState(false);
  const [showSidePanel, setShowSidePanel] = useState(false);
  const [greeting, setGreeting] = useState("");
  const [animationComplete, setAnimationComplete] = useState(false);
  const [isUploadMenuOpen, setIsUploadMenuOpen] = useState(false);
  const [uploads, setUploads] = useState<FileUpload[]>([]);
  const [conversationId] = useState(() => self.crypto.randomUUID());
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const sidePanelRef = useRef<HTMLDivElement>(null);
  const lastScrollTop = useRef(0);
  const isScrollingRef = useRef(false);
  const [cursorPosition, setCursorPosition] = useState(0);

  const [overlayHeight] = useState(150); // Default height in pixels

  const scrollToBottom = useCallback(() => {
    if (messagesEndRef.current && !isScrollingRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, []);

  useEffect(() => {
    const text = "Gracii here, what's up?";
    let i = 0;

    const startTypingEffect = () => {
      const typingEffect = setInterval(() => {
        if (i < text.length) {
          setGreeting((prev) => prev + text.charAt(i));
          i++;
        } else {
          clearInterval(typingEffect);
          setAnimationComplete(true);
        }
      }, 50);

      return () => clearInterval(typingEffect);
    };

    // Add a 1-second delay before starting the animation
    const delay = setTimeout(startTypingEffect, 1000);

    return () => {
      clearTimeout(delay);
    };
  }, []);
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (e.clientX <= 10) {
        setShowSidePanel(true);
      } else if (
        sidePanelRef.current &&
        !sidePanelRef.current.contains(e.target as Node)
      ) {
        setShowSidePanel(false);
      }
    };

    document.addEventListener("mousemove", handleMouseMove);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
    };
  }, []);
  useEffect(() => {
    if (messages.length > 0 && messages[messages.length - 1].role === "bot") {
      scrollToBottom();
    }
  }, [messages, scrollToBottom]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (input.trim()) {
      setHasInteracted(true);
      const userMessage: Message = {
        id: Date.now(),
        content: input,
        role: "user",
      };
      setMessages((prevMessages) => [...prevMessages, userMessage]);
      setInput("");
      setIsStreaming(true);
      setShowHeader(true);

      try {
        const response = await fetch(
          `http://localhost:8000/chat/${conversationId}`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              content: input,
              role: "user",
            }),
          }
        );

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (reader) {
          const botMessageId = Date.now();
          setMessages((prevMessages) => [
            ...prevMessages,
            { id: botMessageId, content: "", role: "bot" },
          ]);

          let text = "";
          let isUsingTool = false;
          while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);

            if (chunk.includes("TOOL_USE")) {
              isUsingTool = true;
              setMessages((prevMessages) =>
                prevMessages.map((msg) =>
                  msg.id === botMessageId
                    ? {
                      ...msg,
                      toolUse: true,
                      toolDone: false,
                      isThinking: false,
                      content: text,
                    }
                    : msg
                )
              );
              continue;
            }

            if (chunk.includes("DONE")) {
              isUsingTool = false;
              setMessages((prevMessages) =>
                prevMessages.map((msg) =>
                  msg.id === botMessageId
                    ? {
                      ...msg,
                      toolUse: false,
                      toolDone: false,
                      isThinking: true,
                      content: text,
                    }
                    : msg
                )
              );
              continue;
            }

            if (!chunk.includes("END_TURN")) {
              text += chunk;
              setMessages((prevMessages) =>
                prevMessages.map((msg) => {
                  if (msg.id === botMessageId) {
                    // If we were thinking and got a new token, mark as done
                    if (msg.isThinking) {
                      return {
                        ...msg,
                        toolDone: true,
                        isThinking: false,
                        content: text,
                      };
                    }
                    return { ...msg, content: text };
                  }
                  return msg;
                })
              );
            }
          }
        }
      } catch (error) {
        console.error("Error:", error);
        setMessages((prevMessages) => [
          ...prevMessages,
          {
            id: Date.now(),
            content: "Sorry, there was an error processing your request.",
            role: "bot",
          },
        ]);
      } finally {
        setIsStreaming(false);
      }
    }
  };

  const handleAttachment = () => {
    setIsUploadMenuOpen(true);
  };

  const handleFileType = (type: FileType) => {
    if (fileInputRef.current) {
      fileInputRef.current.accept = ACCEPTED_FILE_TYPES[type];
      fileInputRef.current.click();
    }
    setIsUploadMenuOpen(false);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length) return;

    const file = files[0];
    const type = getFileType(file.type);

    // Limit to 5 files
    if (uploads.length >= 5) {
      alert("Maximum 5 files allowed");
      return;
    }

    const upload: FileUpload = {
      id: crypto.randomUUID(),
      file,
      type,
      preview: file.type.startsWith("image/")
        ? URL.createObjectURL(file)
        : undefined,
    };

    setUploads((prev) => [...prev, upload]);

    // Clear the file input value so the same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const getFileType = (mimeType: string): FileType => {
    if (mimeType.startsWith("image/")) return "image";
    if (mimeType.includes("pdf") || mimeType.includes("doc")) return "document";
    return "data";
  };

  const removeUpload = (id: string) => {
    setUploads((prev) => {
      const upload = prev.find((u) => u.id === id);
      if (upload?.preview) {
        URL.revokeObjectURL(upload.preview);
      }
      return prev.filter((u) => u.id !== id);
    });

    // Clear input if there are no more uploads
    if (uploads.length <= 1) {
      setInput("");
    }
  };

  const cleanupUploads = () => {
    uploads.forEach((upload) => {
      if (upload.preview) {
        URL.revokeObjectURL(upload.preview);
      }
    });
    setUploads([]);
    setInput("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSelectionChange = (
    e: React.SyntheticEvent<HTMLTextAreaElement>
  ) => {
    const target = e.target as HTMLTextAreaElement;
    setCursorPosition(target.selectionStart || 0);
  };

  useEffect(() => {
    return () => {
      cleanupUploads();
    };
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  const handleScroll = useCallback((e: Event) => {
    const container = e.target as HTMLDivElement;
    if (container) {
      const { scrollTop, scrollHeight, clientHeight } = container;
      const isAtBottom = scrollHeight - scrollTop === clientHeight;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;

      // Only show header when at top or scrolling up
      if (
        scrollTop > 50 &&
        scrollTop > lastScrollTop.current &&
        !isNearBottom
      ) {
        setShowHeader(false);
      } else if (
        scrollTop < lastScrollTop.current ||
        scrollTop === 0 ||
        isAtBottom
      ) {
        setShowHeader(true);
      }

      lastScrollTop.current = scrollTop;
    }
  }, []);

  useEffect(() => {
    const container = chatContainerRef.current;
    if (container) {
      container.addEventListener("scroll", handleScroll);
      return () => container.removeEventListener("scroll", handleScroll);
    }
  }, [handleScroll]);

  const ActionButtons = ({ messageContent }: { messageContent: string }) => {
    const handleCopy = async () => {
      try {
        const cleanContent = messageContent.replace("END_TURN", "").trim();
        await navigator.clipboard.writeText(cleanContent);
        console.log("Content copied to clipboard");
      } catch (err) {
        console.error("Failed to copy text: ", err);
      }
    };

    const TooltipButton = ({
      onClick,
      title,
      children,
    }: {
      onClick?: () => void;
      title: string;
      children: React.ReactNode;
    }) => (
      <div className="group relative">
        <button
          onClick={onClick}
          className="p-2 hover:bg-gray-200 rounded-full"
        >
          {children}
        </button>
        <div className="absolute topo-full left-1/2 transform -translate-x-1/2 mt-2 px-2 py-1 text-xs text-white bg-gray-800 rounded-md opacity-0 group-hover:opacity-100 transition-opacity duration-200 whitespace-nowrap pointer-events-none">
          {title}
        </div>
      </div>
    );

    return (
      <div className="flex gap-0.5 mt-3">
        <TooltipButton title="Listen to this response">
          <svg
            width="17"
            height="17"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-gray-500"
          >
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>
          </svg>
        </TooltipButton>

        <TooltipButton title="Copy to clipboard" onClick={handleCopy}>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-gray-500"
          >
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
          </svg>
        </TooltipButton>

        <TooltipButton title="helpful">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-gray-500"
          >
            <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
          </svg>
        </TooltipButton>

        <TooltipButton title="not helpful">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-gray-500"
          >
            <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3" />
          </svg>
        </TooltipButton>

        <TooltipButton title="Regenerate response">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-gray-500"
          >
            <path d="M23 4v6h-6" />
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
          </svg>
        </TooltipButton>
      </div>
    );
  };

  const containerVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.6,
        ease: "easeOut",
        staggerChildren: 0.1,
      },
    },
  };

  const headerVariants = {
    hidden: { opacity: 0, y: -20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5, ease: "easeOut" },
    },
  };

  const messageVariants = {
    hidden: { opacity: 0, x: 0, scale: 0.5 },
    visible: {
      opacity: 1,
      x: 0,
      scale: 1,
      transition: { duration: 0.2, ease: "easeOut" },
    },
  };

  const streamingTokenVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.3 },
    },
  };

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

  const customComponents = {
    code({
      node,
      inline,
      className,
      children,
      ...props
    }: {
      node: any;
      inline: boolean;
      className: string;
      children: any;
    }) {
      const match = /language-(\w+)/.exec(className || "");
      return !inline ? (
        <div className=" bg-gray-800 m-0 rounded-md max-w-2xl">
          <div className="text-gray-200 bg-gray-700 px-4 py-2 text-xs font-sans m-0 rounded-t-md">
            <span>{match ? match[1] : "code"}</span>
          </div>
          <pre className="bg-gray-800 rounded-b-md max-w-full p-4 m-0 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-gray-800">
            <code
              className="bg-gray-800 text-white px-1 max-w-md py-0.5 text-sm font-mono"
              {...props}
            >
              {children}
            </code>
          </pre>
        </div>
      ) : (
        <code
          className="!whitespace-pre text-white text-sm font-mono"
          {...props}
        >
          {children}
        </code>
      );
    },
    a({
      node,
      href,
      children,
      ...props
    }: {
      node: any;
      href: string;
      children: any;
    }) {
      const isCodeBlock = node.parent?.type === "code";
      return isCodeBlock ? (
        <span className="text-blue-300" {...props}>
          {children}
        </span>
      ) : (
        <a
          href={href}
          className="text-blue-500 hover:underline font-medium"
          target="_blank"
          rel="noopener noreferrer"
          {...props}
        >
          {children}
        </a>
      );
    },
    p({ node, children, ...props }: { node: any; children: any }) {
      const isWithinCodeBlock = node.parent?.type === "code";
      return isWithinCodeBlock ? (
        <span className="block mb-2" {...props}>
          {children}
        </span>
      ) : (
        <p
          className="p-0 m-0 mb-4 font-normal"
          // style={{
          //   fontFamily: "'Afacad Flux', sans-serif",
          //   lineHeight: '1.6',
          // }}
          {...props}
        >
          {children}
        </p>
      );
    },
    pre({ node, children, ...props }: { node: any; children: any }) {
      return (
        <div className="m-0 min-w-full" {...props}>
          {children}
        </div>
      );
    },
    li({ node, children, ...props }: { node: any; children: any }) {
      return (
        <li
          className="mb-1 mt-0 p-0 font-normal" // Added margin bottom to list items
          {...props}
        >
          {children}
        </li>
      );
    },
    h1: ({ node, children, ...props }: { node: any; children: any }) => (
      <h1
        className="text-2xl font-bold mb-4 mt-6 text-gray-800 pb-1"
        {...props}
      >
        {children}
      </h1>
    ),
    h2: ({ node, children, ...props }: { node: any; children: any }) => (
      <h2 className="text-xl font-semibold mb-2 mt-5 text-gray-700" {...props}>
        {children}
      </h2>
    ),
    h3: ({ node, children, ...props }: { node: any; children: any }) => (
      <h3 className="text-base font-medium mb-1 mt-4 text-gray-600" {...props}>
        {children}
      </h3>
    ),
    h4: ({ node, children, ...props }: { node: any; children: any }) => (
      <h4 className="text-sm font-medium mb-1 mt-3 text-gray-600" {...props}>
        {children}
      </h4>
    ),
    h5: ({ node, children, ...props }: { node: any; children: any }) => (
      <h5 className="text-sm font-medium mb-0 mt-2 text-gray-600" {...props}>
        {children}
      </h5>
    ),
    h6: ({ node, children, ...props }: { node: any; children: any }) => (
      <h6 className="text-sm font-medium mb-0 mt-1 text-gray-600" {...props}>
        {children}
      </h6>
    ),
  };

  return (
    <motion.div
      className="flex flex-col h-screen bg-gray-100 text-gray-800"
      initial="hidden"
      animate="visible"
      variants={containerVariants}
    >
      {/* Add global style */}
      <style>
        {`
          ::selection {
            background-color: #FFEB3B; /* yellow background */
            color: #000000; /* black text */
          }
          
          ::-moz-selection {
            background-color: #FFEB3B; /* yellow background for Firefox */
            color: #000000; /* black text for Firefox */
          }
        `}
      </style>

      {/* Side Panel */}
      <div
        ref={sidePanelRef}
        className={`fixed top-0 left-0 h-full bg-gray-200 transition-all duration-300 ease-in-out ${showSidePanel ? "w-64" : "w-0"
          } overflow-hidden z-50`}
      >
        <div className="p-4">
          <h2 className="text-xl font-bold mb-4 text-gray-800">Chat History</h2>
          {/* Add your chat history list here */}
        </div>
      </div>

      {/* Header */}
      <motion.header
        variants={headerVariants}
        className={`z-30 fixed top-0 left-0 right-0 bg-gradient-to-b from-gray-300 to-transparent p-4 text-center transition-transform duration-300 ease-in-out ${showHeader && hasInteracted ? "translate-y-0" : "-translate-y-full"
          }`}
      >
        <h1 className="text-2xl font-bold">Gracii</h1>
      </motion.header>

      {/* Showing Chat Interactive*/}
      <main
        className={`flex-1 overflow-hidden flex flex-col transition-transform duration-300 ${showHeader ? "pt-16" : "pt-0"
          }`}
      >
        <div
          ref={chatContainerRef}
          className="flex-1 overflow-auto scrollbar-hide scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100 relative"
          style={{ height: "100vh" }}
          onScroll={handleScroll}
        >
          {/* Greeting */}
          {!hasInteracted && (
            <motion.div
              className="flex items-center justify-center"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <style>
                {`
                  @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300&display=swap');
                `}
              </style>
              <div className="absolute top-3/4 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                <h1
                  className="text-6xl font-light text-gray-700"
                  style={{
                    fontFamily: "'Poppins', sans-serif",
                    opacity: animationComplete ? 1 : 0.7,
                    transition: "opacity 0.5s ease-in-out",
                  }}
                >
                  {animationComplete ? "Gracii here, what's up?" : greeting}
                </h1>
              </div>
            </motion.div>
          )}

          {/* Overlay message fade */}
          <div className="fixed top-0 left-0 right-0 bottom-0 pointer-events-none z-20">
            <div
              className="bg-gradient-to-b from-gray-100 via-transparent to-transparent"
              style={{ height: `${overlayHeight}px` }} // Use the overlayHeight state here
            ></div>
          </div>

          {/* Chat messages */}
          <div className="max-w-3xl mx-auto pb-24 relative z-10">
            <AnimatePresence mode="sync">
              {messages.map((message, index) => (
                <motion.div
                  key={message.id}
                  className={`flex items-start mb-4 ${message.role === "user" ? "justify-end" : "justify-start"
                    }`}
                  variants={messageVariants}
                  initial="hidden"
                  animate="visible"
                  custom={index}
                >
                  <div
                    className={`flex items-start space-x-2 ${message.role === "user" ? "flex-row-reverse" : "flex-row"
                      }`}
                  >
                    {message.role === "bot" && (
                      <div className="p-2 rounded-full bg-gray-300 mt-4">
                        <div className="w-6 h-6 bg-gray-500 rounded-full flex items-center justify-center self-start">
                          <span className="text-xs font-bold text-white">
                            AI
                          </span>
                        </div>
                      </div>
                    )}
                    <div
                      className={`p-2 ${message.role === "user"
                        ? "bg-gray-200 rounded-3xl max-w-lg shadow-sm px-4"
                        : "bg-gray-100 max-w-full my-4 group/message p-2"
                        }`}
                    >
                      <div className="flex flex-col gap-1">
                        {(message.toolUse ||
                          message.toolDone ||
                          message.isThinking) && (
                            <div className="mb-3">
                              <ToolUseIndicator
                                isDone={message.toolDone}
                                isThinking={message.isThinking}
                              />
                            </div>
                          )}
                        {message.content && (
                          <motion.div
                            initial="hidden"
                            animate="visible"
                            variants={streamingTokenVariants}
                          >
                            <ReactMarkdown
                              className="prose max-w-full space-y-4 prose-p:my-0 prose-pre:my-0"
                              style={
                                `
                                .body{
                                  font-size: 16px;
                                }
                                `
                              }
                              remarkPlugins={[remarkGfm]}
                              components={customComponents}
                            >
                              {message.content.replace("END_TURN", "")}
                            </ReactMarkdown>
                          </motion.div>
                        )}
                        {message.role === "bot" &&
                          (message.content.includes("END_TURN") ||
                            !isStreaming) && (
                            <div
                              className={`${index === messages.length - 1
                                ? "opacity-100"
                                : "opacity-0 group-hover/message:opacity-100"
                                } transition-opacity duration-200`}
                            >
                              <ActionButtons messageContent={message.content} />
                            </div>
                          )}
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
              <div ref={messagesEndRef} />
            </AnimatePresence>
          </div>
        </div>

        {/* Chat Input */}
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
                    className="shrink-0 p-1 text-gray-500 hover:text-gray-700 focus:outline-none self-end mb-3"
                  >
                    <Paperclip className="w-5 h-5" />
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
                    className={`bg-[#000] text-white rounded-full shrink-0 ml-1 mb-3 p-1 focus:outline-none self-end transition-opacity duration-200 ${!input.trim() && uploads.length === 0
                      ? "opacity-10 cursor-not-allowed"
                      : "hover:opacity-70"
                      }`}
                  >
                    <ArrowUp className="w-5 h-5" />
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
      </main>

      {/* File Hander */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        className="hidden"
      />
    </motion.div>
  );
}

export default App;
