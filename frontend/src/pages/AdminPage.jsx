import React, { useEffect, useState } from 'react';
import { getAllUsers, promoteUser } from '../services/api'; // Import promoteUser
import { toast } from 'sonner';
import { Loader, Users, Shield, Trash2 } from 'lucide-react';

const AdminPage = () => {
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isPromoting, setIsPromoting] = useState(null); // Track which user is being promoted

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    setIsLoading(true);
    try {
      const usersData = await getAllUsers();
      setUsers(usersData);
    } catch (error) {
      toast.error(error.message || 'Failed to load users.');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePromote = async (userId) => {
    setIsPromoting(userId);
    try {
        const updatedUser = await promoteUser(userId);
        // Update the user's role in the local state to reflect the change immediately
        setUsers(users.map(u => u.id === userId ? updatedUser : u));
        toast.success(`User ${updatedUser.username} has been promoted to Admin.`);
    } catch (error) {
        toast.error(error.message || 'Failed to promote user.');
    } finally {
        setIsPromoting(null);
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 h-full flex flex-col bg-gray-900">
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-white">Admin Dashboard</h1>
        <p className="text-gray-400">System-wide user management and overview.</p>
      </header>

      <div className="flex-1 bg-gray-950 rounded-2xl p-6 shadow-lg">
        <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
          <Users className="mr-3" /> User Management
        </h2>
        {isLoading ? (
          <div className="flex justify-center mt-8">
            <Loader className="animate-spin h-10 w-10 text-indigo-500" />
          </div>
        ) : (
          <div className="overflow-auto">
            <table className="w-full text-sm text-left text-gray-400">
              <thead className="text-xs text-gray-400 uppercase bg-gray-800">
                <tr>
                  <th scope="col" className="px-6 py-3">Username</th>
                  <th scope="col" className="px-6 py-3">Email</th>
                  <th scope="col" className="px-6 py-3">Role</th>
                  <th scope="col" className="px-6 py-3">Joined On</th>
                  <th scope="col" className="px-6 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(user => (
                  <tr key={user.id} className="bg-gray-950 border-b border-gray-800 hover:bg-gray-800">
                    <td className="px-6 py-4 font-medium text-white">{user.username}</td>
                    <td className="px-6 py-4">{user.email}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full capitalize ${user.role === 'admin' ? 'bg-yellow-900 text-yellow-300' : 'bg-blue-900 text-blue-300'}`}>
                        {user.role}
                      </span>
                    </td>
                    <td className="px-6 py-4">{new Date(user.created_at).toLocaleDateString()}</td>
                    <td className="px-6 py-4 flex items-center space-x-3">
                        {user.role !== 'admin' && ( // Only show the button if the user is not already an admin
                            <button 
                                onClick={() => handlePromote(user.id)}
                                disabled={isPromoting === user.id}
                                className="text-gray-400 hover:text-yellow-400 disabled:text-gray-600 disabled:cursor-not-allowed" 
                                title="Promote to Admin"
                            >
                                {isPromoting === user.id ? <Loader size={16} className="animate-spin" /> : <Shield size={16} />}
                            </button>
                        )}
                        <button className="text-gray-400 hover:text-red-400" title="Delete User (Not Implemented)">
                            <Trash2 size={16} />
                        </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminPage;
