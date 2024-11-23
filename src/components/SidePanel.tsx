interface SidePanelProps {
    sidePanelRef: React.RefObject<HTMLDivElement>;
    showSidePanel: boolean;
}

export const SidePanel = ({ sidePanelRef, showSidePanel }: SidePanelProps) => {
    return (
        <div
            ref={sidePanelRef}
            className={`fixed top-0 left-0 h-full bg-gray-200 transition-all duration-300 ease-in-out ${showSidePanel ? "w-64" : "w-0"
                } overflow-hidden z-50`}
        >
            <div className="p-4">
                <h2 className="text-xl mb-4 text-gray-800">Chat History</h2>
                {/* Add your chat history list here */}
            </div>
        </div>
    )
}