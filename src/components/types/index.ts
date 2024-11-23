export interface Message {
  id: number;
  content: string;
  role: "user" | "bot";
  toolUse?: boolean;
  toolDone?: boolean;
  isThinking?: boolean;
}


// Add other types used across components