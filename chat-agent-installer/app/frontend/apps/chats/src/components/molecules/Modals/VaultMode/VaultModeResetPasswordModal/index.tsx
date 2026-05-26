import { FC, useState } from 'react';
import { App, Modal } from 'antd';

import { useAppDispatch } from '@shared/ui/store';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { resetVaultModePasswordService } from '@/services/vault.services';
import {
  setVaultMode,
  setVaultModeRegistered,
} from '@shared/ui/store/chats/chats.slice';
import useRefetchChats from '@/hooks/useRefetchChats';

import { VaultModeResetPasswordModalProps } from '@/components/molecules/Modals/VaultMode/VaultModeResetPasswordModal/VaultModeResetPasswordModal.props';

const VaultModeResetPasswordModal: FC<VaultModeResetPasswordModalProps> = ({
  className = '',
  onCloseCb = () => {},
  ...props
}) => {
  const dispatch = useAppDispatch();
  const handleError = useHandleError();
  const { message } = App.useApp();
  const { refetchChats } = useRefetchChats();

  const [loading, setLoading] = useState(false);

  const handleResetMode = async () => {
    try {
      setLoading(true);
      await resetVaultModePasswordService();
      dispatch(setVaultMode(false));
      dispatch(setVaultModeRegistered(false));
      await refetchChats();
      message.success(`The password has successfully reset`);
    } catch (e) {
      handleError(e);
    } finally {
      setLoading(false);
      onCloseCb();
    }
  };
  return (
    <Modal
      centered
      title='Reset password'
      okText='Accept'
      onOk={handleResetMode}
      destroyOnHidden
      loading={loading}
      className={`vault-mode-reset-password-modal ${className}`}
      onCancel={() => onCloseCb()}
      {...props}
    >
      By clicking the &#39;Accept&#39; button, you accept that all chats which
      were created under the Vault mode will be deleted
    </Modal>
  );
};

export default VaultModeResetPasswordModal;
