import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { submitComplaint, getSnapshotFromUrl } from '../services/api';
import { toast } from 'sonner';
import { Send, Paperclip, Loader, Image as ImageIcon, Mail } from 'lucide-react';

const ComplaintPage = () => {
  const location = useLocation();
  const incidentData = location.state;

  const [toEmail, setToEmail] = useState('');
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [evidenceFile, setEvidenceFile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const fetchWithRetry = async (url, retries = 4, delay = 2000) => {
      for (let i = 0; i < retries; i++) {
        try {
          const blob = await getSnapshotFromUrl(url);
          return blob;
        } catch (err) {
          if (i < retries - 1) {
            await new Promise(res => setTimeout(res, delay));
          } else {
            throw err;
          }
        }
      }
    };

    if (incidentData) {
      setSubject(`Complaint regarding Incident: ${incidentData.threatType.toUpperCase()}`);
      setMessage(
        `Incident ID: #${incidentData.incidentId}\n` +
        `Timestamp: ${new Date(incidentData.timestamp).toLocaleString()}\n\n` +
        `Please describe the issue in more detail here...\n`
      );

      if (incidentData.snapshotUrl) {
        toast.info("Attempting to attach incident snapshot...");
        fetchWithRetry(incidentData.snapshotUrl)
          .then(blob => {
            const file = new File([blob], `incident_${incidentData.incidentId}_snapshot.jpg`, { type: 'image/jpeg' });
            setEvidenceFile(file);
            toast.success("Snapshot attached as evidence.");
          })
          .catch(err => {
            toast.error("Could not automatically attach snapshot after several attempts.");
            console.error("Snapshot fetch error:", err);
          });
      }
    }
  }, [incidentData]);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      if (e.target.files[0].size > 10 * 1024 * 1024) { // 10MB limit
        toast.error("File size cannot exceed 10MB.");
        e.target.value = null;
        return;
      }
      setEvidenceFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!toEmail.trim() || !subject.trim() || !message.trim()) {
      toast.error("Please fill out all required fields, including the recipient's email.");
      return;
    }
    
    setIsLoading(true);
    
    const formData = new FormData();
    const fullMessage = `I would like to file a complaint regarding Incident: ${incidentData.threatType.toUpperCase()}.\n\n${message}`;
    
    formData.append('to_email', toEmail);
    formData.append('subject', subject);
    formData.append('message', fullMessage);
    if (evidenceFile) {
      formData.append('evidence', evidenceFile);
    }
    if (incidentData?.incidentId) {
        formData.append('incident_id', incidentData.incidentId);
    }

    try {
      await submitComplaint(formData);
      toast.success("Complaint submitted successfully!");
      setToEmail('');
      setSubject('');
      setMessage('');
      setEvidenceFile(null);
      e.target.reset();
    } catch (error) {
      toast.error(error.message || "Failed to submit complaint.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 h-full flex flex-col bg-gray-900">
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-white">Submit a Complaint</h1>
        <p className="text-gray-400">Report a critical incident or provide feedback to officials.</p>
      </header>

      <div className="flex-1 bg-gray-950 rounded-2xl p-6 shadow-lg max-w-2xl mx-auto w-full">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="to-email" className="block text-sm font-medium text-gray-300 mb-1">To (Recipient Email)</label>
            <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={16} />
                <input
                  id="to-email"
                  name="to-email"
                  type="email"
                  placeholder="official.department@example.com"
                  value={toEmail}
                  onChange={(e) => setToEmail(e.target.value)}
                  required
                  className="w-full pl-10 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-indigo-500 focus:border-indigo-500"
                />
            </div>
          </div>

          <div>
            <label htmlFor="subject" className="block text-sm font-medium text-gray-300 mb-1">Subject</label>
            <input
              id="subject"
              name="subject"
              type="text"
              placeholder="e.g., Critical Threat at Lobby Entrance"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              required
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>

          <div>
            <label htmlFor="message" className="block text-sm font-medium text-gray-300 mb-1">Message</label>
            
            {incidentData && (
              <div className="p-3 bg-gray-800 border border-gray-700 rounded-t-lg text-gray-300">
                I would like to file a complaint regarding Incident: <span className="font-bold text-red-500">{incidentData.threatType.toUpperCase()}</span>
              </div>
            )}
            
            <textarea
              id="message"
              name="message"
              placeholder="Details..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              required
              rows="8"
              className={`w-full px-3 py-2 bg-gray-800 border border-gray-700 text-white focus:ring-indigo-500 focus:border-indigo-500 ${incidentData ? 'border-t-0 rounded-b-lg' : 'rounded-lg'}`}
            />
          </div>

          <div>
            <label htmlFor="evidence" className="block text-sm font-medium text-gray-300 mb-1">Attach Evidence</label>
            <div className="mt-2 flex items-center justify-center w-full">
                <label htmlFor="evidence-file-input" className="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-600 border-dashed rounded-lg cursor-pointer bg-gray-800/50 hover:bg-gray-800/80">
                    <div className="flex flex-col items-center justify-center pt-5 pb-6 text-center">
                        {evidenceFile ? (
                             <>
                                <ImageIcon className="w-8 h-8 mb-4 text-green-400" />
                                <p className="text-sm text-green-400">{evidenceFile.name}</p>
                             </>
                        ) : (
                            <>
                                <Paperclip className="w-8 h-8 mb-4 text-gray-400" />
                                <p className="mb-2 text-sm text-gray-400"><span className="font-semibold">Click to upload</span> or drag and drop</p>
                                <p className="text-xs text-gray-500">Video, Image, or Document (MAX. 10MB)</p>
                            </>
                        )}
                    </div>
                    <input id="evidence-file-input" type="file" className="hidden" onChange={handleFileChange} />
                </label>
            </div> 
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={isLoading}
              className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-indigo-400 disabled:cursor-not-allowed"
            >
              {isLoading ? <Loader className="animate-spin -ml-1 mr-3 h-5 w-5" /> : <Send className="-ml-1 mr-3 h-5 w-5" />}
              {isLoading ? 'Submitting...' : 'Submit Complaint'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ComplaintPage;
