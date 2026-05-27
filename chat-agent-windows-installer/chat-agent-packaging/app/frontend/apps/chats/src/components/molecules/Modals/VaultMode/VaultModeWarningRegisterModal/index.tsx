import { FC } from 'react';
import { VaultModeWarningModalProps } from '@/components/molecules/Modals/VaultMode/VaultModeWarningModal/VaultModeWarningModal.props';
import { useRouter } from 'next/router';
import { Modal } from 'antd';

const VaultModeWarningRegisterModal: FC<VaultModeWarningModalProps> = (
  props,
) => {
  const router = useRouter();

  return (
    <Modal
      centered
      title='Register the Vault Mode required'
      okText='Register the Vault Mode'
      destroyOnHidden
      {...props}
      onOk={() => router.push('/vault-mode')}
    >
      Register the Vault mode first, before enabling this mode
    </Modal>
  );
};

export default VaultModeWarningRegisterModal;
