"use client";

import { useState } from "react";
import { Building2, ChevronDown } from "lucide-react";

export function WorkspaceSwitcher() {
  const [isOpen, setIsOpen] = useState(false);
  const [activeWorkspace, setActiveWorkspace] = useState("Personal Workspace");
  
  const workspaces = [
    { id: "1", name: "Personal Workspace" },
    { id: "2", name: "Acme Agency" },
  ];

  return (
    <div className="relative px-4 py-4 border-b border-gray-200 dark:border-gray-800">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 px-3 py-2 rounded-lg transition-colors border border-gray-200 dark:border-gray-700"
      >
        <div className="flex items-center gap-2 overflow-hidden">
          <Building2 className="w-4 h-4 text-indigo-600 dark:text-indigo-400 flex-shrink-0" />
          <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
            {activeWorkspace}
          </span>
        </div>
        <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-4 right-4 mt-1 bg-white dark:bg-[#1E2532] border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-50 py-1">
          <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
            Workspaces
          </div>
          {workspaces.map((ws) => (
            <button
              key={ws.id}
              onClick={() => {
                setActiveWorkspace(ws.name);
                setIsOpen(false);
              }}
              className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors ${
                activeWorkspace === ws.name 
                  ? 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/10' 
                  : 'text-gray-700 dark:text-gray-300'
              }`}
            >
              {ws.name}
            </button>
          ))}
          <div className="border-t border-gray-200 dark:border-gray-700 mt-1 pt-1">
            <button className="w-full text-left px-3 py-2 text-sm text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
              + Create Workspace
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
