// MarkdownComponents.tsx
import { Components } from 'react-markdown'

export const customComponents: Components = {
    code: ({ inline, className, children, ...props }: any) => {
        const match = /language-(\w+)/.exec(className || "");
        return !inline ? (
            <div className="bg-gray-800 m-0 rounded-md max-w-2xl">
                <div className="text-gray-200 bg-gray-700 px-4 py-2 text-xs font-sans m-0 rounded-t-md">
                    <span>{match ? match[1] : "code"}</span>
                </div>
                <pre className="bg-gray-800 rounded-b-md max-w-full p-4 m-0 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-gray-800">
                    <code className="bg-gray-800 text-white px-1 max-w-md py-0.5 text-sm font-mono" {...props}>
                        {children}
                    </code>
                </pre>
            </div>
        ) : (
            <code className="!whitespace-pre text-white text-sm font-mono" {...props}>
                {children}
            </code>
        )
    },

    a({ href, children, ...props }) {
        return (
            <a
                href={href}
                className="text-cyan-500 hover:underline font-medium"
                target="_blank"
                rel="noopener noreferrer"
                {...props}
            >
                {children}
            </a>
        )
    },

    p({ children, ...props }) {
        return (
            <p
                className="p-0 m-0 font-normal"
                style={{
                    fontSize: 16
                }}
                {...props}
            >
                {children}
            </p>
        )
    },

    pre({ children, ...props }) {
        return (
            <pre className="m-0 min-w-full" {...props}>
                {children}
            </pre>
        )
    },

    li({ children, ...props }) {
        return (
            <li className="font-normal text-pretty" {...props}>
                {children}
            </li>
        )
    },

    h1({ children, ...props }) {
        return (
            <h1 className="text-2xl font-bold mb-4 mt-6 text-gray-800 pb-1" {...props}>
                {children}
            </h1>
        )
    },

    h2({ children, ...props }) {
        return (
            <h2 className="text-xl font-semibold mb-2 mt-5 text-gray-700" {...props}>
                {children}
            </h2>
        )
    },

    h3({ children, ...props }) {
        return (
            <h3 className="text-base font-medium mb-1 mt-4 text-gray-600" {...props}>
                {children}
            </h3>
        )
    },

    h4({ children, ...props }) {
        return (
            <h4 className="text-sm font-medium mb-1 mt-3 text-gray-600" {...props}>
                {children}
            </h4>
        )
    },

    h5({ children, ...props }) {
        return (
            <h5 className="text-sm font-medium mb-0 mt-2 text-gray-600" {...props}>
                {children}
            </h5>
        )
    },

    h6({ children, ...props }) {
        return (
            <h6 className="text-sm font-medium mb-0 mt-1 text-gray-600" {...props}>
                {children}
            </h6>
        )
    }
} as Components;