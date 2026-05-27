import { FC } from 'react';
import { Modal } from 'antd';
import { useRouter } from 'next/router';

import { useAppDispatch, useAppSelector } from '@shared/ui/store';
import { setShowEnableVaultModal } from '@shared/ui/store/chats/chats.slice';

import { VaultModeWarningModalProps } from '@/components/molecules/Modals/VaultMode/VaultModeWarningModal/VaultModeWarningModal.props';

const VaultModeWarningModal: FC<VaultModeWarningModalProps> = ({
  onCancel,
  ...props
}) => {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const vaultModeRegistered = useAppSelector(
    (store) => store.chats.vaultModeRegistered,
  );

  const handleAccept = (e: any) => {
    if (!vaultModeRegistered) {
      router.push('/vault-mode');
      return;
    }
    dispatch(setShowEnableVaultModal(true));
    if (onCancel) {
      onCancel(e);
    }
  };

  return (
    <Modal
      title='Vault Mode required'
      okText='Enable Vault Mode'
      {...props}
      onOk={handleAccept}
      onCancel={onCancel}
      destroyOnHidden
      centered
    >
      For choosing this chat, please, enable the Vault mode
    </Modal>
  );
};

export default VaultModeWarningModal;
