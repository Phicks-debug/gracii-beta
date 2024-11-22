import React, { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileUpload,
  FileType,
  ACCEPTED_FILE_TYPES,
} from "./components/FileUpload";
import { ToolUseIndicator } from './components/ToolUseIndicator';
import { ActionButtons } from "./components/ActionButtons";
import { Header } from "./components/Header";
import { SidePanel } from "./components/SidePanel";
import { Message } from "./components/types/index";
import { customComponents } from "./components/MarkdownComponents";
import { Greeting } from "./components/Greeting";
import { OverlayFadeHeader } from "./components/OverlayFadeHeader";
import { ChatInput } from "./components/ChatInput";


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
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const sidePanelRef = useRef<HTMLDivElement>(null);
  const lastScrollTop = useRef(0);
  const isScrollingRef = useRef(false);

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

  // const handleAttachment = () => {
  //   setIsUploadMenuOpen(true);
  // };

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
      if (scrollTop > 50 && scrollTop > lastScrollTop.current && !isNearBottom) {
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

  return (
    <motion.div
      className="flex flex-col h-screen bg-gray-100 text-gray-800"
      initial="hidden"
      animate="visible"
      variants={containerVariants}
    >
      <SidePanel
        sidePanelRef={sidePanelRef}
        showSidePanel={showSidePanel}
      ></SidePanel>

      <Header
        showHeader={showHeader}
        hasInteracted={hasInteracted}
      ></Header>

      {/* Showing Chat Interactive*/}
      <main
        className={`flex-1 overflow-hidden flex flex-col transition-transform duration-300 ${showHeader ? "pt-16" : "pt-0"
          }`}
      >
        <div
          ref={chatContainerRef}
          className="flex-1 overflow-auto scrollbar-hide scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100 relative"
          style={{ height: "100vh" }}
          onScroll={(e: React.UIEvent<HTMLDivElement>) => {
            handleScroll(e.nativeEvent);
          }}
        >

          {!hasInteracted && (
            <Greeting
              animationComplete={animationComplete}
              greeting={greeting}
            ></Greeting>
          )}

          {/* Overlay message fade */}
          <OverlayFadeHeader
            overlayHeight={overlayHeight}
          ></OverlayFadeHeader>

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
        <ChatInput
          input={input}
          setInput={setInput}
          handleSubmit={handleSubmit}
          handleKeyDown={handleKeyDown}
          isStreaming={isStreaming}
          hasInteracted={hasInteracted}
          uploads={uploads}
          isUploadMenuOpen={isUploadMenuOpen}
          setIsUploadMenuOpen={setIsUploadMenuOpen}
          handleFileType={handleFileType}
          removeUpload={removeUpload}
          fileInputRef={fileInputRef}
          handleFileChange={handleFileChange}
        />
      </main>

      {/* File Hander */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        className="hidden"
      />
    </motion.div >
  );
}

export default App;
