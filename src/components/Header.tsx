import { motion } from 'framer-motion';

interface HeaderProps {
    showHeader: boolean;
    hasInteracted: boolean;
}

export const Header = ({ showHeader, hasInteracted }: HeaderProps) => {
    const headerVariants = {
        hidden: { opacity: 0, y: -20 },
        visible: {
            opacity: 1,
            y: 0,
            transition: { duration: 0.5, ease: "easeOut" },
        },
    };

    return (
        <motion.header
            variants={headerVariants}
            className={`z-30 fixed top-0 left-0 right-0 bg-gradient-to-b from-gray-300 to-transparent p-4 text-center transition-transform duration-300 ease-in-out ${showHeader && hasInteracted ? "translate-y-0" : "-translate-y-full"
                }`}
        >
            <h1 className="text-2xl font-bold">Gracii</h1>
        </motion.header>
    );
};