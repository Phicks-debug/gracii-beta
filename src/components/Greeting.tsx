// components/Greeting.tsx
import { motion } from "framer-motion";

interface GreetingProps {
    animationComplete: boolean;
    greeting: string;
}

export const Greeting = ({ animationComplete, greeting }: GreetingProps) => {
    return (
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
    )
};