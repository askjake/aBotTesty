import { FC, useMemo, useState } from 'react';
import { App, Modal, Tooltip } from 'antd';
import dynamic from 'next/dynamic';

import { disableVaultService } from '@/services/vault.services';
import {
  setShowEnableVaultModal,
  setVaultMode,
} from '@shared/ui/store/chats/chats.slice';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { useAppDispatch, useAppSelector } from '@shared/ui/store';
import useRefetchChats from '@/hooks/useRefetchChats';

import IconButton from '@shared/ui/components/atoms/Buttons/IconButton';
import { StyledVaultModeButtonIcon } from '@/components/molecules/Buttons/VaultModeButton/VaultModeButton.styled';
const VaultModeWarningRegisterModal = dynamic(
  () =>
    import('@/components/molecules/Modals/VaultMode/VaultModeWarningRegisterModal'),
  {
    ssr: false,
  },
);
const VaultModePasswordModal = dynamic(
  () =>
    import('@/components/molecules/Modals/VaultMode/VaultModePasswordModal'),
  {
    ssr: false,
  },
);

import { VaultModeButtonProps } from '@/components/molecules/Buttons/VaultModeButton/VaultModeButton.props';

const VaultModeButton: FC<VaultModeButtonProps> = (props) => {
  const dispatch = useAppDispatch();
  const { message } = App.useApp();
  const { refetchChats } = useRefetchChats();
  const handleError = useHandleError();
  const vaultMode = useAppSelector((store) => store.chats.vaultMode);
  const vaultModeRegistered = useAppSelector(
    (store) => store.chats.vaultModeRegistered,
  );
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [showWarnDisableModal, setShowWarnDisableModal] = useState(false);

  const toolTipText = useMemo(
    () =>
      !vaultModeRegistered
        ? 'Setup vault mode'
        : vaultMode
          ? 'Disable vault mode'
          : 'Enable vault mode',
    [vaultModeRegistered, vaultMode],
  );

  const handleClick = () => {
    if (!vaultModeRegistered) {
      setShowRegisterModal(true);
      return;
    }
    if (vaultMode) {
      setShowWarnDisableModal(true);
    } else {
      dispatch(setShowEnableVaultModal(true));
    }
  };

  const handleDisableMode = async () => {
    try {
      await disableVaultService();
      dispatch(setVaultMode(false));
      await refetchChats();
      message.success(`The Vault Mode has successfully disabled`);
    } catch (e) {
      handleError(e);
    } finally {
      setShowWarnDisableModal(false);
    }
  };

  return (
    <>
      <Tooltip title={toolTipText}>
        <IconButton
          type='text'
          onClick={handleClick}
          icon={
            <StyledVaultModeButtonIcon
              $active={vaultMode && vaultModeRegistered}
            />
          }
          {...props}
        />
      </Tooltip>
      <VaultModeWarningRegisterModal
        data-testid='vault-mode-warning-modal'
        open={showRegisterModal}
        onCancel={() => setShowRegisterModal(false)}
      />
      <Modal
        centered
        data-testid='disable-veult-modal'
        open={showWarnDisableModal}
        title='Disable the Vault mode'
        okText='Accept'
        onOk={handleDisableMode}
        onCancel={() => setShowWarnDisableModal(false)}
      >
        By clicking the &#39;Accept&#39; button, you accept that all chats which
        were created under the Vault mode will be disabled
      </Modal>
      <VaultModePasswordModal />
    </>
  );
};

export default VaultModeButton;
