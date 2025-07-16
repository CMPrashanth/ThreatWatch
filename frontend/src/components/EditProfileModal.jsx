import React, { useState, useEffect, useRef } from 'react';
import { X, Info, Copy, CheckCircle, Link as LinkIcon, Loader } from 'lucide-react';
import { generateTelegramLink, getCurrentUser } from '../services/api';
import { toast } from 'sonner';

const EditProfileModal = ({ isOpen, onClose, onSave, user, onLinkSuccess }) => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  
  const [telegramLink, setTelegramLink] = useState('');
  const [isGeneratingLink, setIsGeneratingLink] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  
  const [currentUser, setCurrentUser] = useState(user);

  const [isLoading, setIsLoading] = useState(false);
  
  const pollingIntervalRef = useRef(null);

  useEffect(() => {
    setCurrentUser(user);
    if (user) {
      setUsername(user.username || '');
      setEmail(user.email || '');
      setPhoneNumber(user.phone_number || '');
      setTelegramLink('');
      setIsPolling(false);
    }
  }, [user, isOpen]);

  useEffect(() => {
    if (isPolling) {
      pollingIntervalRef.current = setInterval(async () => {
        try {
          const updatedUser = await getCurrentUser();
          if (updatedUser.telegram_chat_id) {
            toast.success("Telegram account linked successfully!");
            setCurrentUser(updatedUser);
            // --- THIS IS THE FIX (Part 2) ---
            // Notify the parent component of the successful update.
            onLinkSuccess(updatedUser); 
            setIsPolling(false);
          }
        } catch (error) {
          console.error("Polling failed:", error);
        }
      }, 3000);

      const pollingTimeout = setTimeout(() => {
        setIsPolling(false);
        toast.error("Telegram linking timed out. Please try generating a new link.");
      }, 120000);

      return () => {
        clearInterval(pollingIntervalRef.current);
        clearTimeout(pollingTimeout);
      };
    } else {
      clearInterval(pollingIntervalRef.current);
    }
  }, [isPolling, onLinkSuccess]);


  if (!isOpen) return null;

  const handleGenerateLink = async () => {
    setIsGeneratingLink(true);
    try {
        const data = await generateTelegramLink();
        setTelegramLink(data.link);
        setIsPolling(true);
    } catch (error) {
        toast.error("Failed to generate link. Please try again.");
    } finally {
        setIsGeneratingLink(false);
    }
  };

  const handleCopyToClipboard = () => {
    navigator.clipboard.writeText(telegramLink);
    toast.success("Link copied to clipboard!");
  };

  const handleSave = async () => {
    const dataToUpdate = {
        username,
        email,
        phone_number: phoneNumber,
    };
    
    if (password) {
      dataToUpdate.password = password;
    }

    setIsLoading(true);
    await onSave(dataToUpdate);
    setIsLoading(false);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-950 p-8 rounded-2xl shadow-lg w-full max-w-lg relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-500 hover:text-white"><X size={24} /></button>
        <h2 className="text-2xl font-bold text-white mb-6">Edit Profile</h2>
        <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-2">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Username</label>
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Login & Notification Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">New Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Leave blank to keep current password" className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" />
          </div>

          <div className="border-t border-gray-700 pt-4">
            <h3 className="text-lg font-semibold text-white mb-2">Other Notification Channels</h3>
            <div className="space-y-4">
                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">Phone Number (for SMS)</label>
                    <input type="tel" value={phoneNumber} onChange={(e) => setPhoneNumber(e.target.value)} placeholder="+1234567890 (with country code)" className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" />
                </div>
                
                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">Telegram Account</label>
                    {currentUser?.telegram_chat_id ? (
                        <div className="flex items-center justify-between p-3 bg-green-900/50 border border-green-700 rounded-lg">
                            <p className="text-green-300 flex items-center"><CheckCircle size={16} className="mr-2"/> Account Linked</p>
                            <button onClick={handleGenerateLink} className="text-xs text-gray-400 hover:text-white">Relink</button>
                        </div>
                    ) : (
                        <div className="p-3 bg-gray-800/50 border border-gray-700 rounded-lg">
                            <button onClick={handleGenerateLink} disabled={isGeneratingLink || isPolling} className="w-full flex items-center justify-center py-2 px-4 rounded-lg text-white bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed">
                                {isPolling ? <><Loader size={16} className="animate-spin mr-2"/>Waiting for you in Telegram...</> : <><LinkIcon size={16} className="mr-2" />{isGeneratingLink ? 'Generating...' : 'Link Telegram Account'}</>}
                            </button>
                            {telegramLink && (
                                <div className="mt-3">
                                    <p className="text-xs text-gray-400 mb-2">Click the link below to open Telegram and press "Start". The link is valid for 10 minutes.</p>
                                    <div className="flex items-center bg-gray-900 rounded-md p-2">
                                        <a href={telegramLink} target="_blank" rel="noopener noreferrer" className="flex-1 text-indigo-400 text-sm truncate hover:underline">{telegramLink}</a>
                                        <button onClick={handleCopyToClipboard} className="ml-2 p-1 text-gray-400 hover:text-white"><Copy size={14}/></button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
          </div>
        </div>
        <div className="mt-8 flex justify-end space-x-4">
          <button onClick={onClose} className="py-2 px-4 rounded-lg text-white bg-gray-700 hover:bg-gray-600">Close</button>
          <button onClick={handleSave} disabled={isLoading} className="py-2 px-4 rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400">
            {isLoading ? 'Saving...' : 'Save Profile'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default EditProfileModal;
